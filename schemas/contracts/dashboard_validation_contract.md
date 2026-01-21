# Agent Contract: Dashboard Validation

## Input
### `dashboard_definitions[]`
For each dashboard/report:
- `dashboard_name`
- `tool` (Looker/Looker Studio/etc.)
- `queries[]` (SQL or query references)
- `expected_metrics[]`
- `filters`

### `qa_passed_tables`
References to tables/views that are considered validated inputs.

## Output
### `validation_report`
Metric-level comparisons:
- `dashboard_name`
- `metric`
- `dashboard_value`
- `model_value`
- `source_value` (if available)
- `variance_abs`
- `variance_pct`
- `likely_cause`
- `confidence`

### `trust_score`
- `dashboard_name`
- `score` (0–100)
- `drivers[]`
