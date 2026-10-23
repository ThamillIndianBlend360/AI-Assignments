"""Offline regression tests for source selection, citations, and failure handling."""

import json
import unittest
from unittest.mock import Mock

if __package__:
    from .rag import INSUFFICIENT, construct_context, generate_rag_answer, validate_response
else:
    from rag import INSUFFICIENT, construct_context, generate_rag_answer, validate_response


class RAGTests(unittest.TestCase):
    def setUp(self):
        self.hits = [{'chunk_id': 42, 'score': 0.7,
                      'text': 'Employees receive 24 days of paid annual leave.',
                      'metadata': {'section': 'HR > Annual Leave'}}]
        self.payload = {'insufficient_evidence': False, 'sentence_ids': [0]}

    def test_context_uses_actual_source_id_and_full_sentence(self):
        context = construct_context(self.hits)
        self.assertIn('[Source ID: 42 | Section: HR > Annual Leave]', context)
        self.assertIn(self.hits[0]['text'], context)

    def test_answer_is_original_evidence_with_real_citation(self):
        answer, citations, evidence = validate_response(self.payload, self.hits)
        self.assertIn('[Source ID: 42]', answer)
        self.assertEqual(citations, ['Source ID: 42'])
        self.assertEqual(evidence[0]['claim'], self.hits[0]['text'])
        self.assertEqual(evidence[0]['quote'], evidence[0]['claim'])

    def test_invalid_or_noninteger_sentence_id_rejected(self):
        for sid in (-1, 1, 999, True, '0'):
            with self.subTest(sid=sid), self.assertRaises(ValueError):
                validate_response({'insufficient_evidence': False, 'sentence_ids': [sid]}, self.hits)

    def test_unrestricted_claims_cannot_reintroduce_hallucination(self):
        payload = {'insufficient_evidence': False, 'sentence_ids': [0],
                   'claims': [{'text': 'Manager approval is not required.',
                               'chunk_id': 42, 'quote': self.hits[0]['text']}]}
        with self.assertRaises(ValueError):
            validate_response(payload, self.hits)

    def test_duplicate_selection_is_not_repeated(self):
        answer, citations, evidence = validate_response(
            {'insufficient_evidence': False, 'sentence_ids': [0, 0]}, self.hits)
        self.assertEqual(len(evidence), 1)
        self.assertEqual(len(citations), 1)
        self.assertEqual(answer.count(self.hits[0]['text']), 1)

    def test_abstention_has_exact_message_and_no_citations(self):
        result = validate_response({'insufficient_evidence': True, 'sentence_ids': []}, self.hits)
        self.assertEqual(result, (INSUFFICIENT, [], []))

    def test_inconsistent_or_malformed_payloads_rejected(self):
        for payload in ([], {}, {'insufficient_evidence': 'false', 'sentence_ids': []},
                        {'insufficient_evidence': False, 'sentence_ids': []},
                        {'insufficient_evidence': True, 'sentence_ids': [0]}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_response(payload, self.hits)

    def test_no_hits_does_not_call_model(self):
        client = Mock()
        result = generate_rag_answer('Parental leave?', [], client=client)
        self.assertEqual(result['status'], 'insufficient_evidence')
        client.chat.assert_not_called()

    def test_generation_and_malformed_json_handling(self):
        client = Mock()
        client.chat.return_value = {'message': {'content': json.dumps({**self.payload, 'missing_parts': []})}}
        result = generate_rag_answer('Vacation days?', self.hits, client=client, allow_partial=True)
        self.assertEqual(result['status'], 'answered')
        self.assertIn(self.hits[0]['text'], client.chat.call_args.kwargs['messages'][1]['content'])
        client.chat.return_value = {'message': {'content': 'not json'}}
        result = generate_rag_answer('Vacation days?', self.hits, client=client, allow_partial=True)
        self.assertEqual(result['status'], 'validation_rejected')
        self.assertEqual(result['citations'], [])

    def test_connection_error_is_not_disguised_as_missing_evidence(self):
        client = Mock()
        client.chat.side_effect = ConnectionError('Ollama unavailable')
        with self.assertRaises(ConnectionError):
            generate_rag_answer('Vacation days?', self.hits, client=client)

    def test_partial_answer_keeps_supported_fact_and_names_missing_part(self):
        payload = {**self.payload, 'missing_parts': ['parental leave duration']}
        client = Mock()
        client.chat.return_value = {'message': {'content': json.dumps(payload)}}
        result = generate_rag_answer('Compare annual leave and parental leave duration.', self.hits, client=client, allow_partial=True)
        self.assertEqual(result['status'], 'partially_answered')
        self.assertIn(self.hits[0]['text'], result['answer'])
        self.assertIn('Insufficient evidence for: parental leave duration.', result['answer'])
        self.assertEqual(result['citations'], ['Source ID: 42'])

    def test_missing_part_label_cannot_invent_a_new_policy_statement(self):
        payload = {**self.payload, 'missing_parts': ['Parental leave is 100 days']}
        with self.assertRaises(ValueError):
            validate_response(payload, self.hits, 'Compare annual leave and parental leave duration.', True)

    def test_legacy_policy_remains_reproducible(self):
        client = Mock()
        client.chat.return_value = {'message': {'content': json.dumps(self.payload)}}
        result = generate_rag_answer('Vacation days?', self.hits, client=client)
        self.assertEqual(result['status'], 'answered')
        self.assertNotIn('missing_parts', client.chat.call_args.kwargs['format']['properties'])


if __name__ == '__main__':
    unittest.main()
