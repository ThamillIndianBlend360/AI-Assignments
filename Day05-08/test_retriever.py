"""Verify file-backed ingestion and index refresh without downloading models."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import numpy as np

if __package__:
    from . import retriever
else:
    import retriever


class RetrieverTests(unittest.TestCase):
    def setUp(self):
        retriever._index.cache_clear()
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(retriever._index.cache_clear)
        self.path = Path(self.directory.name) / 'policies.md'

    def test_chunks_come_from_file_with_source_context(self):
        self.path.write_text('# Handbook\n## Rules\nA **new** policy.', encoding='utf-8')
        chunks = retriever.load_chunks(self.path)
        self.assertEqual(chunks[0]['text'], 'A new policy.')
        self.assertEqual(chunks[0]['metadata']['source_document'], 'policies.md')
        self.assertEqual(chunks[0]['metadata']['section'], 'Handbook > Rules')
        self.assertEqual(chunks[0]['id'], chunks[0]['metadata']['chunk_index'])

    def test_search_and_refresh_when_file_changes(self):
        self.path.write_text('# Banana\nBanana rule.\n# Apple\nApple rule.', encoding='utf-8')
        model = Mock()
        model.encode.side_effect = lambda texts, **kwargs: np.array([
            [1.0, 0.0] if 'banana' in text.lower() else [0.0, 1.0] for text in texts])
        with patch.object(retriever, '_embedding_model', return_value=model):
            hits = retriever.search('banana', top_k=1, document_path=self.path)
            self.assertEqual(hits[0]['text'], 'Banana rule.')
            self.assertEqual(hits[0]['score'], 1.0)
            old_hash = hits[0]['metadata']['source_sha256']
            retriever.search('banana', document_path=self.path)
            self.assertEqual(model.encode.call_count, 3)  # One index, two queries.
            self.path.write_text('# Updated\nChanged policy.', encoding='utf-8')
            updated = retriever.search('banana', document_path=self.path)
            self.assertEqual(updated[0]['text'], 'Changed policy.')
            self.assertNotEqual(updated[0]['metadata']['source_sha256'], old_hash)
            self.assertEqual(model.encode.call_count, 5)  # New index plus query.

    def test_empty_document_does_not_initialize_model(self):
        self.path.write_text('# Empty', encoding='utf-8')
        with patch.object(retriever, '_embedding_model') as model:
            self.assertEqual(retriever.search('anything', document_path=self.path), [])
            model.assert_not_called()


if __name__ == '__main__':
    unittest.main()
