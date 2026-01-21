# Agent Contract: Data Harmonization

## Input
### `raw_sources[]`
Each item describes a raw first-party dataset to ingest.

Required fields:
- `source_system` (e.g., google_sheets, csv, api, bigquery)
- `source_location` (url/path/table)
- `partner_name`
- `received_at` (ISO date-time)
- `payload` (pointer to data or inline small sample)

Optional:
- `expected_granularity` (daily/weekly/flight)
- `expected_metrics[]`

## Output
### `harmonized_table`
A normalized fact table aligned to the media plan.

Required columns (minimum viable):
- `date`
- `partner_name`
- `package_partner_name`
- `placement_partner_name`
- `metric_name`
- `metric_value`
- `currency` (if spend)
- `source_system`
- `source_location`
- `ingested_at`

### `schema_map`
Mapping from raw columns → normalized fields.
- `raw_column`
- `normalized_field`
- `transform_applied`
- `confidence`
- `notes`

### `run_log`
- `run_id`
- `schema_version`
- `records_read`
- `records_written`
- `warnings[]`
- `errors[]`
