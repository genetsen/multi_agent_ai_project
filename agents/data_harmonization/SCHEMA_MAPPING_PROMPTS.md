# Schema Mapping Prompts & Rules

This document contains the prompts and rule definitions used by the Data Harmonization Agent when performing AI-assisted schema mapping.

---

## Primary Schema Mapping Prompt

Used when analyzing a new data source and proposing column-to-field mappings.

```
You are analyzing a raw data file from a media/advertising partner to map it to our canonical schema.

## Canonical Schema (Target)

Required fields:
- `date` - The date of the data (daily granularity preferred)
- `partner_name` - The partner/vendor providing this data
- `package_partner_name` - The partner's name for the campaign/package/line item
- `placement_partner_name` - The partner's name for the placement/ad/creative
- `metric_name` - Name of the metric (e.g., impressions, clicks, spend)
- `metric_value` - Numeric value of the metric
- `source_system` - System where data originated
- `source_location` - Path/URL to source
- `ingested_at` - When we ingested this data

Optional fields:
- `currency` - ISO currency code if the metric is monetary
- `date_granularity` - daily/weekly/monthly/flight
- `timezone` - Timezone of date values

## Source Data

Partner: {partner_name}
Source System: {source_system}
Source Location: {source_location}

Columns discovered:
{column_profiles}

Sample rows:
{sample_rows}

## Your Task

For each column in the source data:

1. Determine the most likely canonical field it maps to
2. Identify any transform needed (parse_date, parse_number, unpivot, etc.)
3. Assign a confidence score (0.0-1.0)
4. Note any concerns or ambiguities

For metric columns (impressions, clicks, spend, etc.), note that they need to be "unpivoted" - converted from wide format (one column per metric) to long format (metric_name + metric_value rows).

## Output Format

Respond with a JSON object:

{
  "mappings": [
    {
      "source_column": "column_name",
      "target_field": "canonical_field_name",
      "transform": "transform_type",
      "transform_params": {},
      "confidence": 0.0-1.0,
      "reasoning": "brief explanation"
    }
  ],
  "unmapped_columns": [
    {
      "source_column": "column_name",
      "reason": "why it couldn't be mapped",
      "suggestion": "what to do with it"
    }
  ],
  "concerns": [
    "any overall concerns about this mapping"
  ],
  "requires_human_review": true/false,
  "review_reasons": ["if true, why"]
}
```

---

## Ambiguity Resolution Prompt

Used when initial mapping produces multiple candidates with similar confidence.

```
You previously analyzed a data source and found ambiguous mappings. Help resolve them.

## Ambiguous Mapping

Target field: {target_field}
Description: {field_description}

Candidates:
{candidates_with_profiles}

## Resolution Guidelines

Consider:
1. Column naming conventions in media/advertising data
2. The data type and value patterns
3. What would make sense given the partner and source
4. What we've seen from similar partners before

Pick ONE best candidate, or indicate this needs human review.

## Output Format

{
  "resolution": "column_name" or "needs_human_review",
  "confidence": 0.0-1.0,
  "reasoning": "explanation of your choice"
}
```

---

## Date Parsing Prompt

Used when date columns are detected but format is unclear.

```
Analyze this column to determine the date format.

Column name: {column_name}
Sample values:
{sample_values}

Common date formats in media data:
- YYYY-MM-DD (ISO standard)
- MM/DD/YYYY (US format)
- DD/MM/YYYY (European format)
- YYYY/MM/DD
- MMM DD, YYYY (e.g., "Jan 20, 2026")
- DD-MMM-YYYY (e.g., "20-Jan-2026")

Consider:
- Consistency across samples
- Whether day/month could be ambiguous (e.g., is 01/02/2026 Jan 2 or Feb 1?)
- Any time components

## Output Format

{
  "detected_format": "format_string",
  "confidence": 0.0-1.0,
  "ambiguous": true/false,
  "ambiguity_note": "if ambiguous, explain why",
  "parsed_samples": [
    {"raw": "original", "parsed": "YYYY-MM-DD"}
  ]
}
```

---

## Metric Identification Prompt

Used to identify which columns represent metrics that should be unpivoted.

```
Identify metric columns in this dataset that should be unpivoted to our long format.

## Context

We convert wide-format metric data:
| date | campaign | impressions | clicks | spend |

To long-format:
| date | campaign | metric_name | metric_value |

## Known Metric Types

Standard metrics in media/advertising:
- **Delivery metrics:** impressions, views, plays, completed_views
- **Engagement metrics:** clicks, engagements, interactions, likes, shares, comments
- **Conversion metrics:** conversions, leads, signups, purchases, installs
- **Cost metrics:** spend, cost, media_cost, total_cost, cpm, cpc, cpa
- **Rate metrics:** ctr, vtr, cvr, completion_rate (these are derived, usually keep as-is)

## Source Columns

{column_profiles}

## Output Format

{
  "metric_columns": [
    {
      "column_name": "impressions",
      "standard_metric_name": "impressions",
      "metric_type": "delivery",
      "is_monetary": false,
      "confidence": 0.95
    },
    {
      "column_name": "Media Spend ($)",
      "standard_metric_name": "spend",
      "metric_type": "cost",
      "is_monetary": true,
      "detected_currency": "USD",
      "confidence": 0.90
    }
  ],
  "non_metric_columns": [
    {
      "column_name": "campaign_name",
      "role": "dimension",
      "reasoning": "identifier, not a numeric metric"
    }
  ],
  "unknown_columns": [
    {
      "column_name": "custom_field_1",
      "possible_roles": ["metric", "dimension"],
      "needs_review": true
    }
  ]
}
```

---

## Schema Change Detection Prompt

Used when a source that has been processed before shows different columns.

```
A data source we've processed before has changed. Analyze the differences.

## Previous Schema

Columns: {previous_columns}
Last processed: {last_run_date}

## Current Schema

Columns: {current_columns}

## Your Task

1. Identify new columns (added since last run)
2. Identify removed columns (missing from current)
3. Identify renamed columns (same data, different name)
4. Assess impact on our mappings

## Output Format

{
  "changes": {
    "added_columns": [
      {"name": "new_col", "likely_purpose": "...", "mapping_suggestion": "..."}
    ],
    "removed_columns": [
      {"name": "old_col", "was_mapped_to": "...", "impact": "critical/minor"}
    ],
    "renamed_columns": [
      {"old_name": "...", "new_name": "...", "confidence": 0.0-1.0}
    ],
    "unchanged_columns": ["col1", "col2"]
  },
  "overall_impact": "none/minor/major/breaking",
  "recommended_action": "auto_adapt/review_required/manual_intervention",
  "reasoning": "..."
}
```

---

## Validation Rule Definitions

### Rule: DH-001 - Date Range Check

```yaml
rule_id: DH-001
name: Date Range Check
description: Verify dates are within reasonable range
severity: warn
field: date
logic: |
  date >= (today - 730 days) AND date <= today
error_message: "Date {value} is outside expected range (past 2 years to today)"
auto_fix: null
```

### Rule: DH-002 - Non-Negative Metrics

```yaml
rule_id: DH-002
name: Non-Negative Metrics
description: Metric values should not be negative
severity: warn
field: metric_value
logic: |
  metric_value >= 0
error_message: "Metric {metric_name} has negative value: {value}"
auto_fix: null
exceptions:
  - metric_name in ["variance", "change", "delta"]  # These can be negative
```

### Rule: DH-003 - Currency Required for Spend

```yaml
rule_id: DH-003
name: Currency for Monetary Metrics
description: Spend/cost metrics must have currency specified
severity: warn
field: currency
condition: metric_name in ["spend", "cost", "media_cost", "total_cost", "revenue"]
logic: |
  currency IS NOT NULL AND currency != ""
error_message: "Monetary metric {metric_name} is missing currency"
auto_fix:
  action: set_default
  value: "USD"
  note: "Defaulted to USD - verify with partner"
```

### Rule: DH-004 - No Duplicates

```yaml
rule_id: DH-004
name: No Duplicate Rows
description: Each combination of date + package + placement + metric should be unique
severity: fail
composite_key: [date, package_partner_name, placement_partner_name, metric_name]
logic: |
  COUNT(*) OVER (PARTITION BY composite_key) = 1
error_message: "Duplicate row detected for {composite_key}"
auto_fix:
  action: keep_first
  note: "Kept first occurrence, excluded duplicates"
```

### Rule: DH-005 - Known Partner

```yaml
rule_id: DH-005
name: Known Partner Check
description: Partner name should be in our known list
severity: warn
field: partner_name
logic: |
  partner_name IN (SELECT name FROM known_partners)
error_message: "Unknown partner: {value}"
auto_fix: null
trigger_review: true
```

### Rule: DH-006 - Required Fields Not Null

```yaml
rule_id: DH-006
name: Required Fields Present
description: Required fields must not be null
severity: fail
fields: [date, partner_name, package_partner_name, metric_name, metric_value]
logic: |
  {field} IS NOT NULL
error_message: "Required field {field} is null"
auto_fix: null
```

### Rule: DH-007 - Granularity Match

```yaml
rule_id: DH-007
name: Date Granularity Match
description: Date granularity should match expected if specified
severity: warn
condition: expected_granularity IS NOT NULL
logic: |
  CASE expected_granularity
    WHEN 'daily' THEN COUNT(DISTINCT date) >= expected_days * 0.8
    WHEN 'weekly' THEN date values are 7 days apart
    WHEN 'monthly' THEN date values are month boundaries
  END
error_message: "Data granularity appears to be {detected}, expected {expected}"
auto_fix: null
```

### Rule: DH-008 - Known Metric Names

```yaml
rule_id: DH-008
name: Known Metric Names
description: Metric names should be in standard vocabulary
severity: warn
field: metric_name
logic: |
  metric_name IN (SELECT name FROM standard_metrics)
  OR metric_name IN (SELECT name FROM partner_custom_metrics WHERE partner = partner_name)
error_message: "Unknown metric name: {value}"
auto_fix: null
action_on_fail: pass_through_with_flag
```

---

## Partner-Specific Mapping Rules

These rules capture learned patterns for specific partners.

```yaml
partner_rules:
  PartnerA:
    column_aliases:
      "Campaign Name": package_partner_name
      "Placement Name": placement_partner_name
      "Date": date
      "Imps": impressions
      "Media Cost": spend
    date_format: "MM/DD/YYYY"
    currency: "USD"
    notes: "PartnerA always sends data in US date format, costs in USD"

  PartnerB:
    column_aliases:
      "Kampagne": package_partner_name
      "Anzeige": placement_partner_name
      "Datum": date
      "Impressionen": impressions
      "Kosten": spend
    date_format: "DD.MM.YYYY"
    currency: "EUR"
    notes: "PartnerB sends German-language headers"

  PartnerC:
    preprocessing:
      - skip_rows: 3  # First 3 rows are metadata
      - header_row: 4
    column_aliases:
      "Flight": package_partner_name
      "Creative": placement_partner_name
    special_handling:
      - "Metrics are in separate tabs, need to join on Flight+Creative+Date"
```

---

## Feedback Learning Format

When human reviewers correct mappings, capture the feedback for learning.

```json
{
  "feedback_id": "fb-20260121-xyz",
  "run_id": "dh-20260121-abc123",
  "partner_name": "PartnerA",
  "feedback_type": "mapping_correction",
  "original_mapping": {
    "source_column": "Campaign ID",
    "target_field": "package_partner_name",
    "confidence": 0.55
  },
  "corrected_mapping": {
    "source_column": "Campaign ID",
    "target_field": null,
    "correct_target": "ignored - internal ID only",
    "actual_package_column": "Campaign Name"
  },
  "reviewer": "human@company.com",
  "timestamp": "2026-01-21T11:00:00Z",
  "learning_action": "Add to partner_rules: PartnerA.ignore_columns += ['Campaign ID']"
}
```
