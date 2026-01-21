# Email Scanner Agent: Detailed Design

## Overview

The Email Scanner Agent monitors email inboxes for first-party data deliveries from partners. It identifies relevant emails using keyword and pattern matching, extracts attachments and data links, and routes them to the Data Harmonization Agent pipeline—auto-processing known patterns while queuing unknown formats for human review.

---

## Position in Pipeline

```
                              ┌─────────────────────┐
                              │   Email Scanner     │
                              │       Agent         │
                              └──────────┬──────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
           ┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
           │  Auto-Route   │   │  Review Queue   │   │   Discard/    │
           │  to Data      │   │  (human triage) │   │   Archive     │
           │  Harmonization│   │                 │   │               │
           └───────────────┘   └─────────────────┘   └───────────────┘
```

This agent acts as an **upstream feeder** to the Data Harmonization Agent, automatically detecting and preparing data for ingestion.

---

## Processing Pipeline

### Stage 1: Email Retrieval

**Purpose:** Connect to email system and fetch candidate messages.

**Supported Email Sources:**

| Source | Connection Method | Notes |
|--------|-------------------|-------|
| Gmail | Gmail API (OAuth) | Use labels/filters for efficiency |
| Outlook/M365 | Microsoft Graph API | Supports shared mailboxes |
| IMAP | IMAP protocol | Generic fallback |
| Webhook | Inbound parse | Real-time processing via SendGrid, Mailgun, etc. |

**Retrieval Configuration:**

```yaml
email_retrieval:
  mode: polling | webhook
  polling_interval_minutes: 15
  lookback_hours: 24  # For initial scan on startup
  folders_to_scan: ["INBOX", "Partner Data", "Reports"]
  mark_as_read: false  # Don't modify until processed
  max_emails_per_run: 100
```

**Initial Filter (Pre-fetch):**
- Only fetch emails from the last N hours (configurable)
- Apply server-side filters where possible (labels, folders)
- Skip emails already processed (track by message ID)

---

### Stage 2: Email Classification

**Purpose:** Determine if an email contains first-party data.

**Classification Decision Tree:**

```
For each email:
│
├── Does subject match data delivery patterns?
│   └── YES → score += 0.3
│       Patterns: "report", "data", "delivery", "weekly", "daily",
│                 "performance", "metrics", "analytics", "export"
│
├── Does sender domain match known partner domains?
│   └── YES → score += 0.4 (known partner)
│   └── PARTIAL → score += 0.2 (domain contains partner-like terms)
│
├── Does body contain data delivery language?
│   └── YES → score += 0.2
│       Patterns: "attached", "please find", "as requested",
│                 "weekly report", "performance data", "metrics for"
│
├── Does email have attachments with data extensions?
│   └── YES → score += 0.3
│       Extensions: .csv, .xlsx, .xls, .tsv, .json, .xml
│
├── Does email contain links to data sources?
│   └── YES → score += 0.2
│       Patterns: Google Sheets, Dropbox, Box, OneDrive, S3 presigned
│
├── Does body contain inline tabular data?
│   └── YES → score += 0.2
│       Detection: HTML tables, ASCII tables, CSV-like text blocks
│
└── Final Classification:
    score >= 0.5 → DATA_EMAIL (process)
    score 0.3-0.5 → UNCERTAIN (queue for review)
    score < 0.3 → NOT_DATA (skip)
```

**Keyword & Pattern Library:**

```yaml
subject_patterns:
  high_confidence:
    - regex: "\\b(weekly|daily|monthly)\\s+(report|data|metrics)\\b"
    - regex: "\\bperformance\\s+(report|data|export)\\b"
    - regex: "\\b(Q[1-4]|\\d{4})\\s+results\\b"
    - contains: ["data delivery", "analytics report", "media report"]

  medium_confidence:
    - contains: ["attached", "export", "summary"]
    - regex: "\\b(campaign|placement|partner)\\s+\\w+\\b"

body_patterns:
  data_delivery_phrases:
    - "please find attached"
    - "here is the data"
    - "attached is the report"
    - "as discussed"
    - "for your review"
    - "latest numbers"

  metric_mentions:
    - regex: "\\b(impressions|clicks|spend|conversions|views)\\b"
    - regex: "\\b(CPM|CPC|CTR|CPA)\\b"

link_patterns:
  google_sheets: "docs.google.com/spreadsheets"
  dropbox: "dropbox.com"
  box: "box.com/s/"
  onedrive: "1drv.ms|onedrive.live.com"
  s3_presigned: "s3\\.amazonaws\\.com.*X-Amz-Signature"
```

---

### Stage 3: Content Extraction

**Purpose:** Extract all data assets from classified emails.

**Extraction Types:**

#### 3a. Attachment Extraction

```
For each attachment:
│
├── Check file extension
│   ├── .csv, .tsv → Extract as CSV
│   ├── .xlsx, .xls → Extract as Excel (handle multiple sheets)
│   ├── .json → Parse as JSON
│   ├── .xml → Parse as XML
│   ├── .pdf → OCR or table extraction (flag for review)
│   ├── .zip, .gz → Decompress and recurse
│   └── Other → Log and skip
│
├── Validate file integrity
│   ├── File not empty
│   ├── File not corrupted
│   └── File size within limits
│
└── Generate extraction metadata
    ├── filename
    ├── file_size
    ├── detected_encoding
    ├── row_count (if tabular)
    └── column_headers (if tabular)
```

#### 3b. Link Extraction & Resolution

```
For each detected link:
│
├── Classify link type
│   ├── Google Sheets → Extract sheet ID, prepare for Sheets API
│   ├── Dropbox/Box → Generate download URL
│   ├── S3 presigned → Validate expiration, download
│   └── Unknown → Log for manual review
│
├── Attempt resolution
│   ├── Check if accessible (auth may be needed)
│   ├── Download or reference for later fetch
│   └── Extract metadata (title, last modified)
│
└── Handle auth failures
    └── Queue for review with "requires_access" flag
```

#### 3c. Inline Data Extraction

```
Scan email body for:
│
├── HTML tables
│   └── Parse <table> elements, extract rows/columns
│
├── ASCII/text tables
│   └── Detect aligned columns, delimiter patterns
│
├── CSV-like blocks
│   └── Detect comma/tab separated lines
│
└── For each detected table:
    ├── Extract as structured data
    ├── Infer headers (first row or context)
    └── Flag confidence level
```

---

### Stage 4: Partner & Pattern Matching

**Purpose:** Identify the partner and match against known data patterns.

**Partner Identification:**

```
Priority order:
1. Exact sender email match in partner_contacts[]
2. Sender domain match in partner_domains[]
3. Email signature parsing (company name extraction)
4. Subject line parsing (partner name mentions)
5. Historical correlation (this sender previously sent data for Partner X)

If no match:
└── Flag as "unknown_partner", queue for review
```

**Pattern Matching for Auto-Processing:**

```yaml
known_patterns:
  PartnerA:
    sender_patterns: ["*@partnera.com", "reports@partnera-analytics.com"]
    subject_patterns: ["PartnerA Weekly", "PartnerA Performance"]
    expected_format: "xlsx"
    expected_columns: ["Date", "Campaign", "Impressions", "Clicks", "Spend"]
    auto_process: true
    confidence_threshold: 0.8

  PartnerB:
    sender_patterns: ["*@partnerb.io"]
    subject_patterns: ["Daily Export", "PartnerB Data"]
    expected_format: "csv"
    expected_columns: ["date", "campaign_name", "imps", "clicks", "cost"]
    auto_process: true
    confidence_threshold: 0.8

  # Generic pattern for unknown but data-like emails
  _unknown:
    auto_process: false
    action: queue_for_review
```

**Pattern Match Scoring:**

```
For each known pattern:
  match_score = 0

  if sender matches sender_patterns: match_score += 0.3
  if subject matches subject_patterns: match_score += 0.2
  if format matches expected_format: match_score += 0.2
  if columns match expected_columns:
    match_score += 0.3 * (matched_columns / total_expected_columns)

  if match_score >= confidence_threshold:
    → Auto-process with this pattern
  else:
    → Queue for review
```

---

### Stage 5: Routing Decision

**Purpose:** Determine action for each extracted data asset.

**Decision Matrix:**

| Condition | Action | Notes |
|-----------|--------|-------|
| Known partner + known pattern + high confidence | `AUTO_PROCESS` | Send directly to Data Harmonization |
| Known partner + unknown pattern | `REVIEW_QUEUE` | New data format from existing partner |
| Unknown partner + data-like content | `REVIEW_QUEUE` | Potential new partner |
| Known partner + low confidence match | `REVIEW_QUEUE` | Verify before processing |
| No data detected | `ARCHIVE` | Log and skip |
| Processing error | `ERROR_QUEUE` | Technical failure, needs investigation |

**Auto-Process Payload:**

When routing to Data Harmonization Agent:

```json
{
  "raw_sources": [
    {
      "source_system": "email",
      "source_location": "email://message_id/attachment_name",
      "partner_name": "PartnerA",
      "received_at": "2026-01-21T10:30:00Z",
      "payload": {
        "type": "file_reference",
        "path": "/extracted/msg_123/report.xlsx",
        "encoding": "utf-8"
      },
      "email_metadata": {
        "message_id": "<abc123@mail.partnera.com>",
        "from": "reports@partnera.com",
        "subject": "PartnerA Weekly Performance Report",
        "received_date": "2026-01-21T10:30:00Z"
      },
      "expected_granularity": "daily",
      "expected_metrics": ["impressions", "clicks", "spend"],
      "pattern_match": {
        "pattern_id": "PartnerA_weekly",
        "confidence": 0.92
      }
    }
  ]
}
```

**Review Queue Item:**

```json
{
  "review_id": "es-rev-20260121-001",
  "created_at": "2026-01-21T10:35:00Z",
  "email_summary": {
    "message_id": "<xyz789@unknown.com>",
    "from": "data@newpartner.com",
    "subject": "January Analytics",
    "received_date": "2026-01-21T10:30:00Z",
    "body_preview": "Hi, please find attached our monthly report..."
  },
  "classification_score": 0.65,
  "classification_reason": "Data-like content from unknown sender",
  "extracted_assets": [
    {
      "type": "attachment",
      "filename": "jan_report.csv",
      "row_count": 150,
      "columns": ["date", "campaign", "impressions", "clicks"]
    }
  ],
  "suggested_actions": [
    {
      "action": "add_as_new_partner",
      "description": "Register newpartner.com as a new partner"
    },
    {
      "action": "process_once",
      "description": "Process this data without creating a pattern"
    },
    {
      "action": "ignore",
      "description": "Not relevant data, archive email"
    }
  ],
  "reviewer_notes_field": ""
}
```

---

## Edge Cases & Error Handling

### Email Retrieval Issues

| Issue | Detection | Response |
|-------|-----------|----------|
| Auth token expired | API 401 error | Alert, attempt refresh, pause scanning |
| Rate limiting | API 429 error | Exponential backoff, continue later |
| Mailbox unavailable | Connection timeout | Retry with backoff, alert after N failures |
| Email too large | Size > limit | Extract metadata only, flag for manual download |

### Content Extraction Issues

| Issue | Detection | Response |
|-------|-----------|----------|
| Corrupted attachment | Parse failure | Log error, queue for manual inspection |
| Password-protected file | Encryption detected | Queue for review with "needs_password" flag |
| Unsupported format | Unknown extension | Log, include in review queue |
| Empty attachment | 0 bytes or no data rows | Warning, likely placeholder or error |
| Link expired | 404 or access denied | Queue for review, note "link_expired" |
| Link requires auth | 403 or login redirect | Queue for review, note "requires_access" |

### Classification Issues

| Issue | Detection | Response |
|-------|-----------|----------|
| Ambiguous email | Score between 0.3-0.5 | Queue for review |
| Multiple partners mentioned | Multiple pattern matches | Queue for review, present options |
| Forwarded email chain | Fwd:/Re: with nested content | Try to extract original, flag complexity |
| Auto-generated bounce | Mailer-daemon, bounce patterns | Ignore |
| Out of office reply | OOO patterns | Ignore |

---

## Confidence Scoring

### Email Classification Confidence

```
base_score = sum(pattern_match_scores)

adjustments:
  +0.15 if sender in known_contacts
  +0.10 if similar to previously processed emails
  -0.10 if email is part of long thread (reply chain)
  -0.15 if subject contains "Re:" or "Fwd:"
  -0.20 if from personal email domain (gmail, yahoo, etc.)

final_confidence = min(1.0, max(0.0, base_score + adjustments))
```

### Pattern Match Confidence

```
pattern_confidence = weighted_average(
  sender_match_score * 0.25,
  subject_match_score * 0.20,
  format_match_score * 0.25,
  column_match_score * 0.30
)
```

---

## Human Review Interface Requirements

The review queue should support:

1. **Email Preview** - Show sender, subject, body preview, timestamp
2. **Attachment Preview** - Show first N rows of data files
3. **Classification Explanation** - Why was this flagged?
4. **Quick Actions**:
   - Approve & Process (send to Data Harmonization)
   - Add as New Partner (create pattern)
   - Ignore (archive, don't process)
   - Block Sender (add to blocklist)
5. **Pattern Learning** - Option to create new pattern from approved email

---

## Integration Points

### Upstream (Inputs)
- Email servers (Gmail, Outlook, IMAP)
- Webhook endpoints for real-time processing

### Downstream (Outputs)
- **Data Harmonization Agent** - Auto-routed data payloads
- **Review Dashboard** - Items requiring human decision
- **Notification System** - Alerts for errors, new partners, etc.

### Feedback Loop
- Approved review items update known_patterns
- Blocked senders update blocklist
- New partners registered in partner_contacts

---

## Configuration

```yaml
email_scanner_agent:
  # Connection
  email_source: gmail | outlook | imap | webhook
  credentials_secret: "email_scanner_creds"

  # Scanning behavior
  polling_interval_minutes: 15
  folders_to_scan: ["INBOX", "Partner Data"]
  lookback_hours_on_startup: 48
  max_emails_per_run: 100

  # Classification thresholds
  classification_threshold_process: 0.7
  classification_threshold_review: 0.3

  # Pattern matching
  auto_process_confidence_threshold: 0.8
  require_review_for_new_partners: true

  # Content extraction
  max_attachment_size_mb: 50
  supported_extensions: [".csv", ".xlsx", ".xls", ".tsv", ".json"]
  extract_inline_tables: true
  follow_links: true

  # Safety
  blocklisted_senders: ["noreply@*", "mailer-daemon@*"]
  blocklisted_domains: ["spam.com"]

  # Retention
  processed_email_retention_days: 90
  review_queue_timeout_days: 7
```

---

## Observability

### Metrics to Track

| Metric | Description |
|--------|-------------|
| `emails_scanned_total` | Total emails processed |
| `emails_classified_data` | Emails identified as containing data |
| `emails_auto_processed` | Emails sent directly to harmonization |
| `emails_queued_for_review` | Emails requiring human decision |
| `extraction_errors` | Failed attachment/link extractions |
| `pattern_match_rate` | % of data emails matching known patterns |
| `avg_classification_confidence` | Rolling average confidence score |
| `review_queue_depth` | Current items awaiting review |
| `review_turnaround_hours` | Average time from queue to decision |

### Alerts

| Condition | Alert Level | Action |
|-----------|-------------|--------|
| Auth failure | Critical | Immediate notification |
| Review queue > 50 items | Warning | Notify team |
| New partner detected | Info | Notification for awareness |
| Classification confidence dropping | Warning | May indicate pattern drift |
| Extraction error rate > 5% | Warning | Investigate data quality |
