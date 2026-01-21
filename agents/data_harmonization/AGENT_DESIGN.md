# Data Harmonization Agent: Detailed Design

## Overview

The Data Harmonization Agent is the entry point for all first-party data entering the system. It transforms heterogeneous partner data formats into a canonical schema aligned to the media plan, while preserving full data lineage and flagging anomalies for human review.

---

## Processing Pipeline

### Stage 1: Source Ingestion

**Purpose:** Connect to and extract raw data from various source systems.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  raw_sources[]  │────▶│  Source Router   │────▶│  Raw DataFrame  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

**Source Router Logic:**

| source_system | Handler | Notes |
|---------------|---------|-------|
| `google_sheets` | Sheets API or export CSV | Handle tab selection via `payload` |
| `csv` | Direct file read | Detect encoding (UTF-8, Latin-1, etc.) |
| `api` | HTTP client | Handle auth, pagination, rate limits |
| `bigquery` | BQ client | Run query or table extract |
| `s3` | AWS S3 client | Support multiple file formats |
| `sftp` | SFTP client | Common for partner data drops |

**Ingestion Outputs:**
- Raw data as DataFrame/table
- `ingestion_metadata`: row count, column names, file size, detected encoding
- `ingestion_warnings[]`: issues encountered (e.g., truncated rows, encoding fixes)

---

### Stage 2: Schema Discovery

**Purpose:** Analyze raw columns and infer their semantic meaning.

**Discovery Process:**

1. **Column Profiling**
   - Data type detection (string, numeric, date, boolean)
   - Null percentage
   - Unique value count / cardinality
   - Sample values (first 5, random 5)
   - Statistical summary (min, max, mean, median for numerics)

2. **Semantic Classification**

   For each column, assign a `semantic_type` using these heuristics:

   | Pattern | Semantic Type | Confidence Boost |
   |---------|---------------|------------------|
   | Column name contains "date", "day", "period" | `date_field` | +0.3 |
   | Values match ISO date or common date formats | `date_field` | +0.4 |
   | Column name contains "spend", "cost", "revenue" | `currency_metric` | +0.3 |
   | Column name contains "impressions", "clicks", "views" | `count_metric` | +0.3 |
   | Column name contains "partner", "vendor", "source" | `partner_identifier` | +0.3 |
   | Column name contains "campaign", "package", "line" | `package_identifier` | +0.2 |
   | Column name contains "placement", "ad", "creative" | `placement_identifier` | +0.2 |
   | High cardinality + short strings | `identifier_candidate` | +0.1 |
   | Low cardinality + categorical values | `dimension_candidate` | +0.1 |

3. **Ambiguity Detection**

   Flag columns where:
   - Multiple semantic types have similar confidence (within 0.15)
   - Confidence for best match < 0.5
   - Column name is generic (e.g., "value", "amount", "name", "id")

---

### Stage 3: Schema Mapping

**Purpose:** Map discovered columns to canonical schema fields.

**Canonical Schema (Target):**

```yaml
required_fields:
  - date                    # ISO date (YYYY-MM-DD)
  - partner_name            # Partner providing the data
  - package_partner_name    # Partner's package/campaign name
  - placement_partner_name  # Partner's placement/ad name
  - metric_name             # Name of the metric
  - metric_value            # Numeric value
  - source_system           # System of origin
  - source_location         # Path/URL to source
  - ingested_at             # Timestamp of ingestion

optional_fields:
  - currency                # ISO currency code (if spend)
  - date_granularity        # daily/weekly/monthly/flight
  - timezone                # Timezone of date values
```

**Mapping Decision Tree:**

```
For each canonical field:
│
├── Is there a column with exact name match?
│   └── YES → Map with confidence 0.95
│       └── Verify data type compatibility
│
├── Is there a column with fuzzy name match (Levenshtein ≤ 2)?
│   └── YES → Map with confidence 0.75
│       └── Flag for review if critical field
│
├── Is there a column with matching semantic type?
│   └── YES → Map with confidence = semantic_confidence * 0.8
│       └── If multiple candidates, pick highest confidence
│
├── Can the field be derived/computed?
│   └── YES → Document transform, confidence 0.70
│       └── Examples: date from timestamp, currency from context
│
└── NO MATCH
    └── If required field → Error
    └── If optional field → Null with warning
```

**Transform Catalog:**

| Transform | Description | Example |
|-----------|-------------|---------|
| `passthrough` | Direct copy | column_a → date |
| `rename` | Name change only | dt → date |
| `parse_date` | String to date | "01/20/2026" → 2026-01-20 |
| `parse_number` | String to number | "1,234.56" → 1234.56 |
| `extract_currency` | Extract currency code | "$1,234" → USD |
| `split_field` | One column to many | "CampaignA|Placement1" → package, placement |
| `concatenate` | Many columns to one | partner + "_" + region → partner_name |
| `lookup` | Value substitution | "FB" → "Facebook" |
| `unpivot` | Wide to long format | impressions, clicks cols → metric_name, metric_value |
| `constant` | Inject static value | source_system = "google_sheets" |

---

### Stage 4: Data Transformation

**Purpose:** Execute the mapping and transforms to produce harmonized output.

**Processing Steps:**

1. **Pre-transform Validation**
   - Verify all required mappings exist
   - Check for conflicting transforms
   - Estimate output row count

2. **Transform Execution**
   - Apply transforms in dependency order
   - Track row-level lineage (source row ID → output row ID)
   - Capture per-transform metrics (rows affected, nulls created)

3. **Metric Unpivoting**

   Most partner data arrives in "wide" format with metrics as columns. The canonical schema requires "long" format.

   ```
   Wide (Input):
   | date | campaign | impressions | clicks | spend |

   Long (Output):
   | date | campaign | metric_name | metric_value |
   | ...  | ...      | impressions | 1000         |
   | ...  | ...      | clicks      | 50           |
   | ...  | ...      | spend       | 100.00       |
   ```

4. **Post-transform Validation**
   - Row count reconciliation
   - Null check on required fields
   - Data type verification
   - Duplicate detection

---

### Stage 5: Quality Checks

**Purpose:** Apply validation rules before output.

**Built-in Rules:**

| Rule ID | Description | Severity |
|---------|-------------|----------|
| `DH-001` | Date is within expected range (not future, not >2 years old) | warn |
| `DH-002` | Metric values are non-negative | warn |
| `DH-003` | Spend values have currency specified | warn |
| `DH-004` | No duplicate rows (same date + package + placement + metric) | fail |
| `DH-005` | Partner name matches known partner list | warn |
| `DH-006` | Required fields are not null | fail |
| `DH-007` | Date granularity matches expected (if specified in input) | warn |
| `DH-008` | Metric names match expected vocabulary | warn |

**Rule Execution:**

```python
for each row in harmonized_table:
    for each rule in enabled_rules:
        result = rule.evaluate(row)
        if result.failed:
            add_to_warnings_or_errors(result)
            if rule.severity == "fail":
                row.exclude_from_output = True
```

---

## Edge Cases & Error Handling

### Data Quality Issues

| Issue | Detection | Response |
|-------|-----------|----------|
| **Empty file/sheet** | Row count = 0 | Error: "Source contains no data" |
| **Missing headers** | First row looks like data | Warning: "Headers may be missing, using row 1 as headers" |
| **Mixed date formats** | Multiple date patterns in same column | Warning: Parse all, flag unparseable |
| **Currency mixing** | Multiple currencies without indicator | Warning: "Assumed USD, flag for review" |
| **Duplicate columns** | Same header name appears twice | Error: "Duplicate column names" |
| **Truncated data** | Row count < expected | Warning: "Possible truncation" |
| **Encoding issues** | Decode errors | Attempt multiple encodings, log which worked |

### Schema Mapping Issues

| Issue | Detection | Response |
|-------|-----------|----------|
| **Unmappable required field** | No candidate with confidence > 0.3 | Error: "Cannot map required field: {field}" |
| **Ambiguous mapping** | Multiple candidates with similar confidence | Warning: "Ambiguous mapping for {field}", pick highest, flag for review |
| **Type mismatch** | e.g., mapping string column to date field | Attempt parse, error if >5% fail |
| **Unknown metrics** | Metric name not in vocabulary | Warning: Pass through but flag |

### Processing Issues

| Issue | Detection | Response |
|-------|-----------|----------|
| **Source unavailable** | Connection/auth failure | Error with retry suggestion |
| **Rate limiting** | HTTP 429 or similar | Implement backoff, log attempts |
| **Timeout** | Processing > threshold | Error: "Processing timeout", suggest chunking |
| **Memory pressure** | Large file warning | Stream processing, log memory usage |

---

## Confidence Scoring Model

### Schema Mapping Confidence

Each mapping receives a confidence score (0.0 - 1.0):

```
base_confidence = method_confidence[mapping_method]
  where:
    exact_name_match = 0.95
    fuzzy_name_match = 0.75
    semantic_match   = 0.60
    derived_field    = 0.70

adjustments:
    +0.10 if data type matches expected
    +0.05 if sample values look valid
    -0.15 if column has high null rate (>20%)
    -0.10 if column name is generic
    -0.20 if multiple candidates were close

final_confidence = min(1.0, max(0.0, base_confidence + sum(adjustments)))
```

### Run-Level Confidence

The overall run confidence is the minimum of:
- Lowest individual mapping confidence
- (1 - error_rate) where error_rate = rows_with_errors / total_rows
- (1 - warning_rate * 0.5) where warning_rate = rows_with_warnings / total_rows

---

## Human Review Triggers

The agent escalates to human review when:

1. **Low Confidence Mapping** (confidence < 0.6 for any required field)
2. **New Partner** (partner_name not in known list)
3. **Schema Change** (incoming schema differs from last run for same source)
4. **High Error Rate** (>5% of rows have errors)
5. **Metric Anomaly** (values differ by >50% from historical baseline)
6. **First Run** (no prior history for this source)

**Review Queue Item Structure:**

```json
{
  "review_id": "uuid",
  "run_id": "uuid",
  "trigger_reason": "low_confidence_mapping",
  "affected_field": "package_partner_name",
  "proposed_mapping": {
    "source_column": "campaign_name",
    "confidence": 0.52,
    "alternatives": [
      {"column": "line_item", "confidence": 0.48}
    ]
  },
  "sample_values": ["Campaign A", "Campaign B", "Campaign C"],
  "reviewer_actions": ["approve", "reject", "select_alternative", "manual_map"]
}
```

---

## Output Specifications

### harmonized_table

```json
{
  "schema_version": "1.0.0",
  "row_count": 1234,
  "columns": [
    {"name": "date", "type": "date", "null_count": 0},
    {"name": "partner_name", "type": "string", "null_count": 0},
    {"name": "package_partner_name", "type": "string", "null_count": 0},
    {"name": "placement_partner_name", "type": "string", "null_count": 5},
    {"name": "metric_name", "type": "string", "null_count": 0},
    {"name": "metric_value", "type": "decimal", "null_count": 0},
    {"name": "currency", "type": "string", "null_count": 800},
    {"name": "source_system", "type": "string", "null_count": 0},
    {"name": "source_location", "type": "string", "null_count": 0},
    {"name": "source_record_id", "type": "string", "null_count": 0},
    {"name": "ingested_at", "type": "timestamp", "null_count": 0}
  ],
  "data": "pointer:table_location"
}
```

### schema_map

```json
{
  "mappings": [
    {
      "raw_column": "Date",
      "normalized_field": "date",
      "transform_applied": "parse_date",
      "transform_params": {"format": "MM/DD/YYYY"},
      "confidence": 0.92,
      "notes": "Exact name match, date parsing successful"
    },
    {
      "raw_column": "Impressions",
      "normalized_field": "metric_value",
      "transform_applied": "unpivot",
      "transform_params": {"metric_name": "impressions"},
      "confidence": 0.88,
      "notes": "Standard metric name, unpivoted to long format"
    }
  ],
  "unmapped_columns": [
    {
      "raw_column": "internal_notes",
      "reason": "No semantic match to canonical schema",
      "suggested_action": "Ignore or add to schema if needed"
    }
  ]
}
```

### run_log

```json
{
  "run_id": "dh-20260121-abc123",
  "schema_version": "1.0.0",
  "started_at": "2026-01-21T10:00:00Z",
  "completed_at": "2026-01-21T10:02:34Z",
  "duration_seconds": 154,
  "records_read": 5000,
  "records_written": 4980,
  "records_excluded": 20,
  "overall_confidence": 0.87,
  "warnings": [
    {
      "code": "DH-001",
      "message": "3 rows have dates in the future",
      "affected_rows": [101, 102, 103]
    }
  ],
  "errors": [
    {
      "code": "DH-004",
      "message": "20 duplicate rows detected and excluded",
      "affected_rows": [...]
    }
  ],
  "human_review_required": false,
  "review_items": []
}
```

---

## Configuration Options

```yaml
data_harmonization_agent:
  # Source handling
  max_file_size_mb: 500
  supported_encodings: ["utf-8", "latin-1", "cp1252"]
  date_formats_to_try: ["YYYY-MM-DD", "MM/DD/YYYY", "DD-MM-YYYY", "YYYY/MM/DD"]

  # Mapping behavior
  fuzzy_match_threshold: 2  # Max Levenshtein distance
  min_confidence_for_auto_map: 0.6
  require_review_for_new_partners: true

  # Quality thresholds
  max_error_rate_before_fail: 0.05
  max_warning_rate_before_review: 0.20

  # Known vocabularies
  known_partners: ["PartnerA", "PartnerB", "PartnerC"]
  known_metrics: ["impressions", "clicks", "spend", "views", "conversions"]

  # Enabled rules
  enabled_rules: ["DH-001", "DH-002", "DH-003", "DH-004", "DH-005", "DH-006"]
```

---

## Integration Points

### Upstream (Inputs)
- Partner data drops (SFTP, email, API)
- Google Sheets/Docs
- Cloud storage (S3, GCS)
- Data warehouses (BigQuery, Snowflake)

### Downstream (Outputs)
- **Classification Agent:** Receives `harmonized_table` for taxonomy mapping
- **Audit/Logging System:** Receives `run_log` for monitoring
- **Review Dashboard:** Receives review items for human intervention
- **Data Catalog:** Receives `schema_map` for documentation

### Feedback Loop
- Human review decisions are captured and used to:
  - Improve confidence scoring weights
  - Add to known partner/metric vocabularies
  - Create explicit mapping rules for future runs
