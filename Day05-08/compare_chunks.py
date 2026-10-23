"""Run offline chunking, integrity checks, and six evidence-based comparisons."""

import argparse
import json
from pathlib import Path
import sys

if __package__:
    from .chunkers import fixed_size_chunks, structural_chunks
    from .metadata import enrich_chunks
    from .parser import load_document
else:
    from chunkers import fixed_size_chunks, structural_chunks
    from metadata import enrich_chunks
    from parser import load_document


DAY_DIR = Path(__file__).resolve().parent


def check_integrity(document, chunks, records) -> None:
    """Fail on missing content, corrupt offsets, or incomplete metadata."""
    if len(chunks) != len(records):
        raise ValueError("Chunk/metadata counts differ")
    cursor = 0
    for index, (chunk, record) in enumerate(zip(chunks, records)):
        meta = record["metadata"]
        if not (0 <= chunk.start < chunk.end <= len(document.text)):
            raise ValueError("Invalid chunk offsets")
        if chunk.text != document.text[chunk.start:chunk.end] or record["text"] != chunk.text:
            raise ValueError("Chunk content does not match normalized source")
        if chunk.start > cursor and document.text[cursor:chunk.start].strip():
            raise ValueError("Chunking lost source content")
        cursor = max(cursor, chunk.end)
        if (meta["chunk_index"] != index or meta["source_document"] != document.source_document
                or meta["chunk_strategy"] != chunk.strategy or not meta["section_heading"]
                or meta["start_char"] != chunk.start or meta["end_char"] != chunk.end
                or meta["heading_paths"] != [list(p) for p in chunk.heading_paths]):
            raise ValueError("Invalid chunk metadata")
    if document.text[cursor:].strip():
        raise ValueError("Chunking lost the end of the document")


def evaluate(document, chunks, records) -> list[dict]:
    results = []

    def result(test, status, evidence):
        results.append({"test": test, "status": status, "evidence": evidence})

    def block_for(heading, kind):
        return next((b for b in document.blocks
                     if b.heading_path and b.heading_path[-1] == heading and b.kind == kind), None)

    policy = block_for("Temporary Access", "paragraph")
    if policy:
        hits = [i for i, c in enumerate(chunks) if c.start < policy.end and c.end > policy.start]
        whole = [i for i, c in enumerate(chunks) if c.start <= policy.start and c.end >= policy.end]
        result("1 - Boundary preservation", "PASS" if whole else "WARN", {
            "rule": policy.text, "rule_characters": len(policy.text),
            "intersecting_chunks": hits, "chunks_with_complete_rule": whole,
            "finding": "Complete rule and expiry exception stay together." if whole
                       else "No chunk contains the complete rule; readers must join fragments.",
        })
    else:
        result("1 - Boundary preservation", "SKIP", "Temporary Access policy probe absent.")

    checklist = block_for("Approval Checklist", "list")
    if checklist:
        hits = [i for i, c in enumerate(chunks) if c.start < checklist.end and c.end > checklist.start]
        context_ok = bool(hits) and all(checklist.heading_path in chunks[i].heading_paths for i in hits)
        result("2 - Heading relationship", "PASS" if context_ok else "WARN", {
            "expected_heading": " > ".join(checklist.heading_path),
            "chunks": hits,
            "reconstructed_paths": {str(i): records[i]["metadata"]["heading_paths"] for i in hits},
            "finding": "Heading paths reconstruct the parent context, including crossed sections.",
        })
    else:
        result("2 - Heading relationship", "SKIP", "Approval Checklist probe absent.")

    detail = "Emergency contact: extension 771."
    if detail in document.text:
        hits = [i for i, c in enumerate(chunks) if detail in c.text]
        lengths = [len(chunks[i].text) for i in hits]
        diluted = bool(hits) and all(len(detail) / length < 0.05 for length in lengths)
        isolated = bool(hits) and all(chunks[i].text.strip() == detail for i in hits)
        result("3 - Small detail", "PASS" if hits and not diluted and not isolated else "WARN", {
            "detail": detail, "chunks_with_complete_detail": hits,
            "containing_chunk_lengths": lengths,
            "detail_fraction": [round(len(detail) / length, 3) for length in lengths],
            "finding": ("Detail split across windows." if not hits else
                        "Detail isolated from supporting context." if isolated else
                        "Detail below 5% of every containing chunk (dilution heuristic)." if diluted else
                        "Detail retained with surrounding incident context."),
        })
    else:
        result("3 - Small detail", "SKIP", "Emergency contact probe absent.")

    pairs = []
    for i, (left, right) in enumerate(zip(chunks, chunks[1:])):
        shared = max(0, min(left.end, right.end) - max(left.start, right.start))
        pairs.append({"chunks": [i, i + 1], "repeated_characters": shared,
                      "repeated_text": document.text[right.start:right.start + shared]})
    repeated = sum(p["repeated_characters"] for p in pairs)
    total = sum(len(c.text) for c in chunks)
    result("4 - Overlap duplication", "PASS", {
        "repeated_characters": repeated,
        "fraction_of_emitted_characters": round(repeated / total, 3) if total else 0,
        "neighbor_pairs": pairs,
        "finding": ("Overlap supplies local boundary context, but does not guarantee complete rules."
                    if repeated else "No duplicated characters; whole sections supply context."),
    })

    if records:
        chosen = next((r for r in records if "extension 771" in r["text"]), records[0])
        result("5 - Metadata", "PASS", chosen["metadata"])
    else:
        result("5 - Metadata", "SKIP", "Document has no body chunks.")

    mixed = []
    for heading, kind in (("Response Targets", "table"), ("Approval Checklist", "list")):
        block = block_for(heading, kind)
        if block:
            whole = [i for i, c in enumerate(chunks) if c.start <= block.start and c.end >= block.end]
            mixed.append({"heading": heading, "kind": kind, "parsed_text": block.text,
                          "chunks_preserving_entire_block": whole})
    result("6 - Mixed structure", "PASS" if mixed and all(
        item["chunks_preserving_entire_block"] for item in mixed) else "WARN" if mixed else "SKIP",
        {"blocks": mixed, "finding": "Whole tables retain column labels; whole lists retain item relationships."
         if mixed else "Sample list/table probes absent."})
    return results


def compare(document, chunk_size=400, overlap=50) -> dict:
    report = {"source_document": document.source_document,
              "normalized_characters": len(document.text), "parsed_blocks": len(document.blocks),
              "settings": {"chunk_size": chunk_size, "overlap": overlap}, "strategies": {}}
    for strategy, chunks in (("fixed_size", fixed_size_chunks(document, chunk_size, overlap)),
                             ("structural", structural_chunks(document))):
        records = enrich_chunks(chunks, document.source_document)
        check_integrity(document, chunks, records)
        lengths = [len(c.text) for c in chunks]
        report["strategies"][strategy] = {
            "chunk_count": len(chunks), "min_characters": min(lengths, default=0),
            "max_characters": max(lengths, default=0),
            "mean_characters": round(sum(lengths) / len(lengths), 1) if lengths else 0,
            "chunks_over_fixed_size_target": sum(length > chunk_size for length in lengths),
            "checks": evaluate(document, chunks, records), "chunks": records,
        }
    return report


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--document", type=Path, default=DAY_DIR / "sample_doc.md")
    cli.add_argument("--chunk-size", type=int, default=400)
    cli.add_argument("--overlap", type=int, default=50)
    cli.add_argument("--output", type=Path, help="Optional JSON report path within Day05-08/")
    args = cli.parse_args(argv)
    try:
        if args.output and not args.output.resolve().is_relative_to(DAY_DIR):
            raise ValueError("Output must be inside Day05-08/")
        document = load_document(args.document)
        report = compare(document, args.chunk_size, args.overlap)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Document: {report['source_document']} | {report['normalized_characters']} normalized characters")
    print(f"Fixed window: {args.chunk_size} characters | overlap: {args.overlap} characters")
    print("Integrity checks: PASS (source coverage, offsets, metadata)")
    for strategy, data in report["strategies"].items():
        print(f"\n{strategy}: {data['chunk_count']} chunks | lengths {data['min_characters']}.."
              f"{data['max_characters']} | mean {data['mean_characters']}")
        print(f"Chunks above the fixed-size target: {data['chunks_over_fixed_size_target']}")
        for check in data["checks"]:
            print(f"\n  {check['test']}: {check['status']}")
            print("  " + json.dumps(check["evidence"], ensure_ascii=False))
    print("\nPASS/WARN describe probe outcomes; SKIP means a sample probe is absent.")
    print("Structural sections preserve complete rules but can exceed the character target.")
    if args.output:
        print(f"JSON report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
