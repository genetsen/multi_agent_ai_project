# Agent Contract: Quality Assurance (QA)

## Input
### `classified_table`
Output from Classification Agent.

### `media_plan_metadata`
Flight windows, planned totals, expected joins.

## Output
### `qa_results`
Row/field-level validation flags.

Columns:
- `record_key` (composite key or hash)
- `severity` (pass/warn/fail)
- `rule_id`
- `rule_description`
- `field`
- `observed_value`
- `expected_range_or_condition`
- `explanation`

### `qa_summary`
- `pass_count`
- `warn_count`
- `fail_count`
- `top_issues[]`
