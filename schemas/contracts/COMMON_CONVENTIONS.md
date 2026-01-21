# Common Contract Conventions

All agent contracts share these conventions.

## Required fields (where applicable)
- `run_id`: unique id for the agent run
- `input_provenance`: where inputs came from (file, table, message ids, timestamps)
- `schema_version`: semantic version for the contract payload
- `confidence`: 0–1 confidence score for key decisions
- `explanations`: short, structured rationale (not freeform only)
- `errors` / `warnings`: machine-readable lists with human-friendly messages

## Data lineage
Every row-level output should be traceable back to source via:
- `source_system`
- `source_location` (URL/path/table)
- `source_record_id` (if available)
- `ingested_at`
