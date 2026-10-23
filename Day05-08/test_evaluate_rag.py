"""Test the rubric against convincing but incorrect outputs, without a model."""

from copy import deepcopy
import unittest

if __package__:
    from . import evaluate_rag as evaluation
else:
    import evaluate_rag as evaluation


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.cases = {c['id']: c for c in evaluation.read_json(evaluation.DAY_DIR/'day08_cases.json')['cases']}
        self.chunks = evaluation.retriever.load_chunks()

    def response(self, section, quote):
        source = next(c for c in self.chunks if c['metadata']['section'].split(' > ')[-1] == section)
        hit = {'chunk_id': source['id'], 'metadata': source['metadata'], 'text': source['text'], 'score': 0.7}
        return {'status': 'answered', 'answer': f"{source['metadata']['section']}: {quote} [Source ID: {source['id']}]",
                'citations': [f"Source ID: {source['id']}"],
                'evidence': [{'chunk_id': source['id'], 'claim': quote, 'quote': quote}],
                'retrieved_chunks': [hit]}

    def test_valid_quote_does_not_imply_relevant_answer(self):
        response = self.response('Annual Leave', 'Annual leave must be requested two weeks in advance.')
        result = evaluation.assess(self.cases['D08-01'], response, self.chunks)
        self.assertTrue(result['checks']['answer_grounded'])
        self.assertTrue(result['checks']['citation_support'])
        self.assertFalse(result['checks']['answer_relevant'])

    def test_partial_answer_requires_explicit_missing_information(self):
        response = self.response('Annual Leave', 'Employees receive 24 days of paid annual leave per calendar year.')
        result = evaluation.assess(self.cases['D08-07'], response, self.chunks)
        self.assertFalse(result['checks']['insufficient_evidence_handling'])
        response['missing_parts'] = ['parental leave duration']
        response['answer'] += '\nInsufficient evidence for: parental leave duration.'
        response['status'] = 'partially_answered'
        result = evaluation.assess(self.cases['D08-07'], response, self.chunks)
        self.assertTrue(result['passed'])

    def test_finance_approval_amount_is_not_a_receipt_threshold(self):
        response = self.response('Approval Checklist', '- For claims over INR 10,000, obtain finance approval.')
        result = evaluation.assess(self.cases['D08-05'], response, self.chunks)
        self.assertTrue(result['checks']['answer_grounded'])
        self.assertFalse(result['checks']['answer_relevant'])
        self.assertFalse(result['checks']['insufficient_evidence_handling'])

    def test_unsupported_correct_abstention(self):
        response = {'status': 'insufficient_evidence', 'answer': evaluation.rag.INSUFFICIENT,
                    'citations': [], 'evidence': [], 'retrieved_chunks': []}
        result = evaluation.assess(self.cases['D08-06'], response, self.chunks)
        self.assertTrue(result['passed'])
        self.assertIsNone(result['checks']['retrieval_success'])

    def test_fake_citation_and_unrecorded_claim_do_not_pass(self):
        response = self.response('Annual Leave', 'Employees receive 24 days of paid annual leave per calendar year.')
        response['citations'] = ['Source ID: 999']
        response['answer'] += '\nParental leave is 100 days.'
        result = evaluation.assess(self.cases['D08-01'], response, self.chunks)
        self.assertFalse(result['checks']['citation_support'])
        self.assertFalse(result['checks']['answer_grounded'])

    def test_changed_source_or_rubric_rejects_comparison(self):
        baseline = {'state': 'complete', 'variant': 'baseline', 'controls': {'source': 'one'},
                    'evaluator_sha256': 'rubric', 'cases': [], 'summary': {}}
        improved = deepcopy(baseline)
        improved['variant'] = 'improved'
        improved['controls']['source'] = 'two'
        with self.assertRaises(ValueError):
            evaluation.compare_reports(baseline, improved)
        improved['controls'] = baseline['controls']
        improved['evaluator_sha256'] = 'changed'
        with self.assertRaises(ValueError):
            evaluation.compare_reports(baseline, improved)


if __name__ == '__main__':
    unittest.main()
