"""Day 08: case-level RAG evaluation without an LLM judge.

Run baseline first, then change ONE response policy and rerun the same dataset.
python Day05-08/evaluate_rag.py --variant baseline
python Day05-08/evaluate_rag.py --variant improved
python Day05-08/evaluate_rag.py --compare Day05-08/day08_baseline.json Day05-08/day08_improved.json
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import inspect
import json
from pathlib import Path
import re
import sys
from time import perf_counter

if __package__:
    from . import rag, retriever
else:
    import rag
    import retriever

DAY_DIR = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def group_found(group, items):
    return any(item['section'].split(' > ')[-1] == expected['section']
               and expected['text'] in item['text'] for expected in group for item in items)


def assess(case, response, source_chunks):
    """Separate provenance from case-specific relevance and missing information."""
    sources = {c['id']: c for c in source_chunks}
    hits = response.get('retrieved_chunks', [])
    evidence = response.get('evidence', [])
    answer = response.get('answer') or ''
    behavior = case['expected_behavior']
    retrieved_items = [{'section': h['metadata']['section'], 'text': h['text']} for h in hits]
    selected_items = [{'section': sources[e['chunk_id']]['metadata']['section'], 'text': e['quote']}
                      for e in evidence if e.get('chunk_id') in sources]
    groups = case['evidence_groups']
    retrieval_ok = all(group_found(g, retrieved_items) for g in groups) if groups else None
    required_selected = all(group_found(g, selected_items) for g in groups)
    hit_ids = {h['chunk_id'] for h in hits}
    provenance = all(e.get('chunk_id') in hit_ids and e.get('chunk_id') in sources
                     and isinstance(e.get('quote'), str) and bool(e['quote'])
                     and e.get('claim') == e['quote']
                     and e['quote'] in sources[e['chunk_id']]['text']
                     and any(e['quote'] in h['text'] for h in hits if h['chunk_id'] == e['chunk_id'])
                     for e in evidence)
    expected_citations = list(dict.fromkeys(f"Source ID: {e['chunk_id']}" for e in evidence))
    answer_citations = list(dict.fromkeys('Source ID: '+s for s in re.findall(r'\[Source ID: (\d+)\]', answer)))
    citations_ok = provenance and response.get('citations') == expected_citations == answer_citations
    absent_parts = response.get('missing_parts', [])
    valid_absence_labels = isinstance(absent_parts, list) and all(
        isinstance(p, str) and bool(p.strip()) and p.casefold() in case['question'].casefold()
        and f'Insufficient evidence for: {p}.' in answer for p in absent_parts)
    expected_lines = [f"{sources[e['chunk_id']]['metadata']['section']}: {e['quote']} [Source ID: {e['chunk_id']}]"
                      for e in evidence if e.get('chunk_id') in sources]
    if absent_parts and valid_absence_labels:
        expected_lines += [f'Insufficient evidence for: {p}.' for p in absent_parts]
    rendered_ok = answer == '\n'.join(expected_lines) if evidence else answer == rag.INSUFFICIENT
    grounded = provenance and rendered_ok and valid_absence_labels
    abstained = response.get('status') == 'insufficient_evidence' and answer == rag.INSUFFICIENT and not evidence and not response.get('citations')
    missing_topic = case.get('missing_topic', '').casefold()
    partial_missing = bool(absent_parts) and valid_absence_labels and any(missing_topic in p.casefold() for p in absent_parts)
    forbidden = [pattern for pattern in case.get('forbidden_answer_patterns', []) if re.search(pattern, answer)]
    if behavior == 'unsupported':
        missing_ok = abstained
        relevant = abstained
    elif behavior == 'missing_detail':
        missing_ok = (abstained or partial_missing) and not forbidden
        relevant = missing_ok
    elif behavior == 'partial':
        missing_ok = partial_missing and not abstained
        relevant = required_selected and missing_ok
    else:
        missing_ok = None
        relevant = required_selected and response.get('status') in ('answered', 'partially_answered')
    operational = response.get('status') in ('execution_error', 'validation_rejected')
    if operational:
        grounded = relevant = citations_ok = False
        if missing_ok is not None:
            missing_ok = False
    context_items = [{'section': h['metadata']['section'], 'text': rag.construct_context([h])} for h in hits]
    context_ok = all(group_found(g, context_items) for g in groups) if groups else None
    checks = {'retrieval_success': retrieval_ok, 'context_preserved': context_ok,
              'answer_grounded': grounded, 'answer_relevant': relevant,
              'citation_support': citations_ok, 'insufficient_evidence_handling': missing_ok}
    failures = []
    if operational:
        failures.append('execution' if response['status'] == 'execution_error' else 'output_validation')
    if retrieval_ok is False:
        failures.append('retrieval')
    elif context_ok is False:
        failures.append('context')
    if not citations_ok:
        failures.append('citation')
    if not grounded:
        failures.append('groundedness')
    if missing_ok is False:
        failures.append('missing_evidence_handling')
    if not relevant and not operational:
        failures.append('answer_relevance')
    return {'checks': checks, 'passed': all(value is not False for value in checks.values()),
            'failure_category': failures[0] if failures else None, 'failure_categories': failures,
            'notes': {'required_evidence_selected': required_selected,
                      'forbidden_answer_patterns_matched': forbidden,
                      'abstained': abstained, 'missing_topic_explicit': partial_missing,
                      'review': 'Deterministic rubric result. Inspect full evidence/answer for semantic correctness; quotations alone do not prove relevance.'}}


def summarize(cases):
    return {'total': len(cases), 'passed': sum(c['evaluation']['passed'] for c in cases),
            'failed': [c['id'] for c in cases if not c['evaluation']['passed']],
            'failure_categories': dict(Counter(category for c in cases for category in c['evaluation']['failure_categories'])),
            'check_failures': {name: sum(c['evaluation']['checks'][name] is False for c in cases)
                               for name in ('retrieval_success', 'context_preserved', 'answer_grounded', 'answer_relevant', 'citation_support', 'insufficient_evidence_handling')}}


def run(dataset_path, variant, model, top_k, output):
    dataset = read_json(dataset_path)
    cases = dataset['cases']
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Dataset case IDs must be unique')
    chunks = retriever.load_chunks()
    # Validate positive expectations against the actual source before evaluation.
    source_items = [{'section': c['metadata']['section'], 'text': c['text']} for c in chunks]
    for case in cases:
        if not all(group_found(g, source_items) for g in case['evidence_groups']):
            raise ValueError(f"Expected source evidence is absent for {case['id']}; review the dataset")
    import ollama
    client = ollama.Client(timeout=180)
    models = client.list().models
    resolved = next((m for m in models if m.model in (model, model+':latest')), None)
    if resolved is None:
        raise ValueError(f'Ollama model not installed: {model}')
    manifest = {'dataset_sha256': digest(dataset_path), 'document_sha256': digest(retriever.DOCUMENT_PATH),
                'normalized_document_sha256': chunks[0]['metadata']['source_sha256'],
                'model': model, 'model_digest': resolved.digest, 'top_k': top_k,
                'embedding_model': retriever.EMBEDDING_MODEL,
                'retrieval_code_sha256': digest(DAY_DIR/'retriever.py'),
                'parser_code_sha256': digest(DAY_DIR/'parser.py'),
                'chunker_code_sha256': digest(DAY_DIR/'chunkers.py'),
                'metadata_code_sha256': digest(DAY_DIR/'metadata.py'),
                'generation_options': {'temperature': 0, 'num_predict': 100, 'num_ctx': 4096}}
    report = {'variant': variant, 'state': 'running', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'controls': manifest, 'rag_code_sha256': digest(DAY_DIR/'rag.py'),
              'rag_source_snapshot': (DAY_DIR/'rag.py').read_text(encoding='utf-8-sig'),
              'evaluator_sha256': digest(Path(__file__)),
              'interpretation': 'Case-level checks plus manual inspection; no LLM judge. Null checks are not applicable, not a pass.',
              'cases': []}
    for number, case in enumerate(cases, 1):
        if digest(dataset_path) != manifest['dataset_sha256'] or digest(retriever.DOCUMENT_PATH) != manifest['document_sha256']:
            raise ValueError('Dataset/source changed during evaluation; do not compare this incomplete run')
        print(f"{variant}: {number}/{len(cases)} {case['id']} {case['category']}", flush=True)
        started = perf_counter()
        hits = []
        try:
            hits = rag.retrieve(case['question'], top_k)
            kwargs = {'model': model, 'client': client}
            if 'allow_partial' in inspect.signature(rag.generate_rag_answer).parameters:
                kwargs['allow_partial'] = variant == 'improved'
            elif variant == 'improved':
                raise ValueError('Improved response policy is not implemented yet')
            response = rag.generate_rag_answer(case['question'], hits, **kwargs)
        except Exception as error:
            response = {'question': case['question'], 'retrieved_chunks': hits,
                        'answer': None, 'citations': [], 'evidence': [], 'status': 'execution_error', 'error': str(error)}
        evaluation = assess(case, response, chunks)
        report['cases'].append({**case, 'elapsed_seconds': round(perf_counter()-started, 3),
                                'response': response, 'evaluation': evaluation})
        report['summary'] = summarize(report['cases'])
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"  {'PASS' if evaluation['passed'] else 'FAIL'} {evaluation['failure_categories']}", flush=True)
    report['state'] = 'complete'
    report['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report['summary'], indent=2))
    return report


def compare_reports(baseline, improved):
    if baseline['state'] != 'complete' or improved['state'] != 'complete':
        raise ValueError('Both runs must be complete')
    if baseline['variant'] != 'baseline' or improved['variant'] != 'improved':
        raise ValueError('Compare a baseline run followed by an improved run')
    if baseline['controls'] != improved['controls']:
        raise ValueError('Controlled comparison rejected: dataset, source, model, options, or retrieval changed')
    if baseline['evaluator_sha256'] != improved['evaluator_sha256']:
        raise ValueError('Evaluation logic changed between runs')
    before = {c['id']: c for c in baseline['cases']}
    after = {c['id']: c for c in improved['cases']}
    if before.keys() != after.keys():
        raise ValueError('Case sets differ')
    changes = []
    for cid, b in before.items():
        a = after[cid]
        old, new = b['evaluation']['passed'], a['evaluation']['passed']
        transition = 'improved' if not old and new else 'regressed' if old and not new else 'unchanged'
        if b['response']['retrieved_chunks'] != a['response']['retrieved_chunks']:
            raise ValueError(f'Retrieved evidence differs for {cid}; investigate before attributing improvement')
        changes.append({'id': cid, 'transition': transition, 'baseline_passed': old, 'improved_passed': new,
                        'baseline_failures': b['evaluation']['failure_categories'],
                        'improved_failures': a['evaluation']['failure_categories']})
    return {'controlled_comparison': True, 'changed_variable': 'Response contract for explicit missing parts; retrieval, source, model, and decoding options fixed.',
            'baseline': baseline['summary'], 'improved': improved['summary'], 'cases': changes,
            'limits': 'One run per variant on a small synthetic corpus; no claim of statistical significance or production readiness.'}


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--dataset', type=Path, default=DAY_DIR/'day08_cases.json')
    cli.add_argument('--variant', choices=('baseline', 'improved'), default='baseline')
    cli.add_argument('--model', default='llama3')
    cli.add_argument('--top-k', type=int, default=3)
    cli.add_argument('--output', type=Path)
    cli.add_argument('--compare', nargs=2, type=Path, metavar=('BASELINE', 'IMPROVED'))
    cli.add_argument('--force', action='store_true', help='Explicitly replace an existing report')
    args = cli.parse_args(argv)
    output = args.output or DAY_DIR/('day08_comparison.json' if args.compare else f'day08_{args.variant}.json')
    if not output.resolve().is_relative_to(DAY_DIR):
        cli.error('Output must be inside Day05-08/')
    if output.exists() and not args.force:
        cli.error('Report already exists; use a different --output or --force to replace it')
    if args.top_k <= 0:
        cli.error('--top-k must be positive')
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        if args.compare:
            result = compare_reports(*(read_json(p) for p in args.compare))
            output.write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result, indent=2))
        else:
            result = run(args.dataset, args.variant, args.model, args.top_k, output)
        return int(any(c.get('response', {}).get('status') == 'execution_error' for c in result['cases']))
    except Exception as error:
        print(f'Evaluation error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
