"""Offline regression checks for preservation, offsets, and strategy tradeoffs."""

from pathlib import Path
import unittest

if __package__:
    from .parser import parse_markdown, load_document
    from .chunkers import fixed_size_chunks, structural_chunks
    from .metadata import enrich_chunks
    from .compare_chunks import compare, check_integrity
else:
    from parser import parse_markdown, load_document
    from chunkers import fixed_size_chunks, structural_chunks
    from metadata import enrich_chunks
    from compare_chunks import compare, check_integrity


class PipelineTests(unittest.TestCase):
    def test_cleaning_keeps_meaning_and_code(self):
        doc = parse_markdown("\ufeff# Handbook\r\n## Rules\r\nA **bold** rule with\r\n"
                             "[a link](https://example.invalid).\r\n\r\n"
                             "<!-- hidden\r\nnote -->\r\n```text\r\n"
                             "key_name: **literal**\r\n  indented\r\n```\r\n")
        self.assertEqual(doc.blocks[0].text, "A bold rule with a link.")
        self.assertEqual(doc.blocks[0].heading_path, ("Handbook", "Rules"))
        self.assertEqual(doc.blocks[1].text, "key_name: **literal**\n  indented")
        self.assertNotIn("hidden", doc.text)
        for block in doc.blocks:
            self.assertEqual(doc.text[block.start:block.end], block.text)

    def test_lists_tables_and_heading_hierarchy(self):
        doc = parse_markdown("# Root\n## Group\n### Items\n- **First**\n- Second\n\n"
                             "| Code | Target |\n| --- | --- |\n| P1 | 15 minutes |\n"
                             "## Other\nA new section.")
        chunks = structural_chunks(doc)
        self.assertEqual(len(chunks), 2)
        self.assertIn("- First\n- Second", chunks[0].text)
        self.assertIn("| Code | Target |\n| P1 | 15 minutes |", chunks[0].text)
        self.assertEqual(chunks[1].heading_paths, (("Root", "Other"),))

    def test_fixed_windows_reconstruct_source_and_overlap(self):
        doc = parse_markdown("# A\n" + "abcdefghij" * 13)
        chunks = fixed_size_chunks(doc, 40, 10)
        recovered = chunks[0].text
        for left, right in zip(chunks, chunks[1:]):
            self.assertEqual(left.text[-10:], right.text[:10])
            recovered += right.text[10:]
        self.assertEqual(recovered, doc.text)
        self.assertEqual(chunks[-1].end, len(doc.text))
        self.assertTrue(all(len(c.text) == 40 for c in chunks[:-1]))

    def test_exact_end_does_not_emit_redundant_tail(self):
        doc = parse_markdown("x" * 70)
        self.assertEqual(len(fixed_size_chunks(doc, 40, 10)), 2)

    def test_crossed_headings_have_all_contexts(self):
        doc = parse_markdown("# One\nAlpha.\n# Two\nBeta.", "policy.md")
        chunks = fixed_size_chunks(doc)
        records = enrich_chunks(chunks, doc.source_document)
        self.assertEqual(records[0]["metadata"]["heading_paths"], [["One"], ["Two"]])
        self.assertEqual(records[0]["metadata"]["source_document"], "policy.md")
        check_integrity(doc, chunks, records)

    def test_same_named_sections_remain_separate(self):
        doc = parse_markdown("# Repeated\nFirst.\n# Repeated\nSecond.")
        self.assertEqual([c.text for c in structural_chunks(doc)], ["First.", "Second."])

    def test_empty_preamble_and_heading_only_input(self):
        for text in ("", "\n  \n", "# Empty\n## Also empty"):
            doc = parse_markdown(text)
            self.assertEqual(fixed_size_chunks(doc), [])
            self.assertEqual(structural_chunks(doc), [])
            compare(doc)
        doc = parse_markdown("Opening context.\n# Topic\nBody.")
        records = enrich_chunks(structural_chunks(doc), "source.md")
        self.assertEqual(records[0]["metadata"]["section_heading"], "Preamble")
        self.assertEqual([r["metadata"]["chunk_index"] for r in records], [0, 1])

    def test_invalid_window_configuration(self):
        doc = parse_markdown("body")
        for size, overlap in ((0, 0), (-1, 0), (10, -1), (10, 10), (10, 11), (True, 0), (10, 1.5)):
            with self.subTest(size=size, overlap=overlap), self.assertRaises(ValueError):
                fixed_size_chunks(doc, size, overlap)

    def test_integrity_detects_missing_content_and_bad_metadata(self):
        doc = parse_markdown("x" * 900)
        chunks = fixed_size_chunks(doc)
        with self.assertRaises(ValueError):
            check_integrity(doc, chunks[1:], enrich_chunks(chunks[1:], "<memory>"))
        records = enrich_chunks(chunks, "<memory>")
        records[0]["metadata"]["chunk_index"] = 99
        with self.assertRaises(ValueError):
            check_integrity(doc, chunks, records)

    def test_sample_comparison_shows_real_boundary_tradeoff(self):
        doc = load_document(Path(__file__).with_name("sample_doc.md"))
        report = compare(doc)
        fixed = report["strategies"]["fixed_size"]["checks"]
        structural = report["strategies"]["structural"]["checks"]
        self.assertEqual(len(fixed), 6)
        self.assertEqual(fixed[0]["status"], "WARN")
        self.assertEqual(structural[0]["status"], "PASS")
        self.assertTrue(all(c["status"] == "PASS" for c in structural))
        self.assertGreater(fixed[3]["evidence"]["repeated_characters"], 0)
        self.assertEqual(structural[3]["evidence"]["repeated_characters"], 0)


if __name__ == "__main__":
    unittest.main()
