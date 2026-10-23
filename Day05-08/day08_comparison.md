# Day 08: RAG Evaluation Comparison

**Decision: keep the baseline.** The experimental partial-evidence policy reduced
passing cases from **9/12 to 6/12** and was rejected.

## Experiment

Evaluated 12 questions using the existing RAG. The only change was a response
policy allowing supported answers plus explicit `missing_parts` notes. Source,
dataset, model, retrieval, Top-K=3, decoding settings, and evaluation rules stayed
fixed. No LLM judge was used.

## Results

| Measurement | Baseline | Candidate |
| --- | --- | --- |
| Cases passed | 9/12 | 6/12 |
| Answer-relevance failures | 3 | 6 |
| Missing-evidence handling failures | 2 | 3 |
| Output-validation failures | 0 | 4 |
| Retrieval/context failures | 0 | 0 |

No cases improved. Cases **03, 06, and 10 regressed**. Failure categories overlap;
validation failures indicate rejected outputs, not observed fake citations.

## Key Findings

- **Wrong threshold:** both variants returned INR 10,000 finance approval as the
  receipt threshold. A real quote and valid citation can still answer the wrong question.
- **Partial information:** the baseline refused the entire annual/parental-leave
  comparison despite having annual-leave evidence. The candidate output was rejected.
- **Unnecessary refusal:** neither variant correctly answered the temporary-access
  exception, although the evidence was retrieved.
- **Candidate regressions:** inconsistent abstention fields caused four validation
  rejections; the annual/sick comparison also omitted sick-leave evidence.

## Recommendation

Retain baseline behavior as the default; keep the candidate opt-in for inspection.
Next, test a simpler response state that cannot express contradictory abstention
fields. Run another iteration before a customer pilot, with HR, finance, and
security reviewing expected behavior.

All **32 automated tests passed**, but live RAG quality remains imperfect. These
results cover one run per variant on a small fictional corpus.

## Evidence

- [Dataset](day08_cases.json)
- [Baseline results](day08_baseline.json)
- [Candidate results](day08_improved.json)
- [Per-case comparison](day08_comparison.json)

The candidate filename `day08_improved.json` identifies the experiment, not an
actual improvement. See [readme.md](readme.md) for run commands.
