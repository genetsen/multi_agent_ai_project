# Data Harmonization Agent

## Role

The Data Harmonization Agent is the entry point for all first-party data entering the multi-agent system. It transforms heterogeneous partner data formats into a canonical schema aligned to the media plan, while preserving full data lineage and flagging anomalies for human review.

## Key Responsibilities

1. **Source Ingestion** - Connect to various data sources (Google Sheets, CSV, APIs, cloud storage)
2. **Schema Discovery** - Profile columns and infer semantic meaning
3. **Schema Mapping** - Map source columns to canonical schema with confidence scores
4. **Data Transformation** - Execute mappings including metric unpivoting (wide → long format)
5. **Quality Validation** - Apply validation rules and flag issues
6. **Lineage Tracking** - Maintain traceability from output rows back to source records

## Documentation

| Document | Description |
|----------|-------------|
| [AGENT_DESIGN.md](./AGENT_DESIGN.md) | Full technical design with processing pipeline, decision trees, and edge cases |
| [SCHEMA_MAPPING_PROMPTS.md](./SCHEMA_MAPPING_PROMPTS.md) | LLM prompts and validation rules for AI-assisted mapping |
| [Contract](../../schemas/contracts/data_harmonization_contract.md) | Input/output contract specification |
| [Example Input](../../schemas/examples/data_harmonization_input.example.json) | Sample input payload |
| [Example Output](../../schemas/examples/data_harmonization_output.example.json) | Sample output with harmonized table, schema map, and run log |

## Processing Pipeline

```
raw_sources[] → Ingestion → Discovery → Mapping → Transform → Validate → Output
                    ↓            ↓          ↓          ↓           ↓
              ingestion_log  profiles   schema_map  harmonized  run_log
                                                      _table    + warnings
                                                                + errors
```

## Outputs

| Output | Description |
|--------|-------------|
| `harmonized_table` | Normalized fact table with canonical schema |
| `schema_map` | Documentation of column mappings and transforms |
| `run_log` | Execution metadata, warnings, errors, and review items |

## Human-in-the-Loop Triggers

The agent escalates to human review when:
- Confidence on any required field mapping < 0.6
- New/unknown partner detected
- Schema changed from previous run
- Error rate > 5%
- First-time processing of a source

## Downstream Consumer

The **Classification Agent** consumes `harmonized_table` to map partner naming conventions to internal taxonomy.

## Configuration

Key configuration options (see AGENT_DESIGN.md for full list):
- `min_confidence_for_auto_map`: Threshold for automatic mapping (default: 0.6)
- `known_partners[]`: List of recognized partner names
- `known_metrics[]`: Standard metric vocabulary
- `enabled_rules[]`: Which validation rules to apply
