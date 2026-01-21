# Agent Contract: Email Scanner

## Overview

The Email Scanner Agent monitors email inboxes for first-party data deliveries, extracts data assets (attachments, links, inline tables), and routes them to the Data Harmonization pipeline or human review queue.

---

## Input

### `scan_config`

Configuration for the scan operation:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email_source` | string | Yes | Source type: `gmail`, `outlook`, `imap`, `webhook` |
| `credentials_ref` | string | Yes | Reference to stored credentials |
| `folders` | string[] | No | Folders to scan (default: `["INBOX"]`) |
| `since` | timestamp | No | Only process emails after this time |
| `message_ids` | string[] | No | Specific messages to process (for reprocessing) |

### `pattern_registry`

Known partner patterns for auto-processing:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `patterns[]` | array | Yes | List of partner patterns |
| `patterns[].partner_name` | string | Yes | Partner identifier |
| `patterns[].sender_patterns` | string[] | Yes | Email/domain patterns |
| `patterns[].subject_patterns` | string[] | No | Subject line patterns |
| `patterns[].expected_format` | string | No | Expected file format |
| `patterns[].expected_columns` | string[] | No | Expected column names |
| `patterns[].auto_process` | boolean | Yes | Whether to auto-route |
| `patterns[].confidence_threshold` | float | No | Min confidence for auto (default: 0.8) |

### `blocklist`

Senders/domains to ignore:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `senders` | string[] | No | Blocked email addresses |
| `domains` | string[] | No | Blocked domains |

---

## Output

### `scan_results`

Summary of the scan operation:

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Unique identifier for this scan |
| `started_at` | timestamp | Scan start time |
| `completed_at` | timestamp | Scan end time |
| `emails_scanned` | integer | Total emails examined |
| `emails_classified_as_data` | integer | Emails identified as containing data |
| `assets_extracted` | integer | Total data assets extracted |
| `auto_processed` | integer | Assets sent to Data Harmonization |
| `queued_for_review` | integer | Assets requiring human decision |
| `errors` | integer | Extraction/processing errors |

### `auto_process_payloads[]`

Data assets routed directly to Data Harmonization Agent:

| Field | Type | Description |
|-------|------|-------------|
| `payload_id` | string | Unique identifier |
| `source_email` | object | Email metadata (message_id, from, subject, date) |
| `partner_name` | string | Identified partner |
| `pattern_match` | object | Pattern ID and confidence score |
| `raw_source` | object | Formatted for Data Harmonization input |
| `routing_timestamp` | timestamp | When sent to harmonization |

Each `raw_source` conforms to Data Harmonization Agent input contract:

```json
{
  "source_system": "email",
  "source_location": "email://{message_id}/{asset_name}",
  "partner_name": "PartnerA",
  "received_at": "timestamp",
  "payload": {
    "type": "file_reference",
    "path": "/extracted/path/to/file"
  },
  "email_metadata": {
    "message_id": "string",
    "from": "string",
    "subject": "string",
    "received_date": "timestamp"
  }
}
```

### `review_queue[]`

Items requiring human review:

| Field | Type | Description |
|-------|------|-------------|
| `review_id` | string | Unique identifier |
| `created_at` | timestamp | When queued |
| `priority` | string | `high`, `medium`, `low` |
| `review_reason` | string | Why review is needed |
| `email_summary` | object | Email preview (from, subject, body snippet) |
| `classification_score` | float | Classification confidence (0-1) |
| `extracted_assets[]` | array | Data found (type, filename, preview) |
| `suggested_partner` | string | Best guess partner (if any) |
| `suggested_actions[]` | array | Possible reviewer actions |
| `expires_at` | timestamp | Review timeout |

### `errors[]`

Processing errors encountered:

| Field | Type | Description |
|-------|------|-------------|
| `error_id` | string | Unique identifier |
| `email_id` | string | Affected email message_id |
| `error_type` | string | Category: `extraction`, `auth`, `network`, `parse` |
| `error_message` | string | Human-readable description |
| `recoverable` | boolean | Can be retried |
| `timestamp` | timestamp | When error occurred |

### `run_log`

Execution log following common conventions:

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Matches scan_results.run_id |
| `schema_version` | string | Contract version |
| `input_provenance` | object | Config and pattern registry used |
| `confidence` | float | Overall scan confidence |
| `warnings[]` | array | Non-fatal issues |
| `errors[]` | array | Fatal issues |

---

## Confidence Scoring

### Email Classification Confidence

Score indicating likelihood email contains first-party data (0.0 - 1.0):

| Factor | Weight | Criteria |
|--------|--------|----------|
| Subject patterns | 0.30 | Matches data delivery keywords |
| Sender recognition | 0.25 | Known partner or data-like domain |
| Attachment presence | 0.25 | Has data file attachments |
| Body patterns | 0.10 | Contains delivery language |
| Link presence | 0.10 | Contains data source links |

### Pattern Match Confidence

Score indicating how well email matches a known pattern (0.0 - 1.0):

| Factor | Weight | Criteria |
|--------|--------|----------|
| Column match | 0.30 | Expected columns present |
| Sender match | 0.25 | Matches sender patterns |
| Format match | 0.25 | Expected file format |
| Subject match | 0.20 | Matches subject patterns |

---

## Review Actions

Supported actions for review queue items:

| Action | Description | Effect |
|--------|-------------|--------|
| `approve_and_process` | Send to Data Harmonization | Routes asset, logs decision |
| `add_as_new_partner` | Create new partner pattern | Adds to pattern_registry |
| `create_pattern` | Define pattern for future | Auto-process similar emails |
| `ignore` | Not relevant data | Archives email, no processing |
| `block_sender` | Add to blocklist | Future emails ignored |
| `defer` | Review later | Extends expiration |

---

## Error Codes

| Code | Description | Severity |
|------|-------------|----------|
| `ES-001` | Email authentication failed | fail |
| `ES-002` | Rate limit exceeded | warn (retry) |
| `ES-003` | Attachment extraction failed | warn |
| `ES-004` | Link resolution failed | warn |
| `ES-005` | Unsupported file format | warn |
| `ES-006` | File corrupted or empty | warn |
| `ES-007` | Password-protected file | warn |
| `ES-008` | Classification ambiguous | info |
| `ES-009` | Unknown partner detected | info |
| `ES-010` | Pattern confidence below threshold | info |

---

## Integration

### Upstream Dependencies
- Email server (Gmail API, Microsoft Graph, IMAP)
- Credentials store

### Downstream Consumers
- **Data Harmonization Agent** - Receives `auto_process_payloads[]`
- **Review Dashboard** - Displays `review_queue[]`
- **Alerting System** - Notified of `errors[]`

### Feedback Inputs
- Review decisions update `pattern_registry`
- Blocked senders update `blocklist`
