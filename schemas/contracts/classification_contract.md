# Agent Contract: Classification (Naming & Taxonomy)

## Input
### `harmonized_table`
Output from Data Harmonization Agent.

Required columns:
- `partner_name`
- `package_partner_name`
- `placement_partner_name`
- `date`
- `metric_name`
- `metric_value`

### `reference_media_plan`
A reference dataset of internal taxonomy and known mappings.

## Output
### `classified_table`
Adds internal identifiers + taxonomy.

Added columns:
- `package_internal_id`
- `placement_internal_id`
- `channel`
- `format`
- `match_method` (exact/fuzzy/model/human_override)
- `match_confidence`
- `match_explanation` (short rationale)
- `original_partner_value` (preserved)

### `exceptions_queue`
Rows requiring review:
- `reason`
- `suggested_matches[]`
- `confidence`
