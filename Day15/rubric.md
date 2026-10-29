# Day 15 Evaluation Rubric: Answer Completeness & Faithfulness

## Criterion 1: Answer Completeness & Faithfulness (LLM-as-Judge)

### Level 3 (Pass / Excellent)
- Fully addresses all parts of the user query.
- Accurately utilizes retrieved policy document facts or tool execution outputs.
- Contains zero hallucinations or ungrounded assertions.
- Includes appropriate document citations where applicable.

### Level 2 (Partial / Marginal)
- Answers the primary question but misses a secondary part or constraint.
- Omits required document citations or source references.
- Technically correct facts but poorly formatted or slightly ambiguous response.

### Level 1 (Fail / Unacceptable)
- Contains fabricated dates, phone numbers, or policy details not present in references.
- Invokes state-changing tools without prior user confirmation.
- Ignores tool errors or provides completely off-topic responses.