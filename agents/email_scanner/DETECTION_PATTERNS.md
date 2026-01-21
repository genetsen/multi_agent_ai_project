# Email Scanner Detection Patterns

This document defines the pattern matching rules used by the Email Scanner Agent to identify first-party data emails and route them appropriately.

---

## Subject Line Patterns

### High Confidence (score += 0.30)

```yaml
high_confidence_subjects:
  # Explicit report/data mentions
  - regex: "\\b(weekly|daily|monthly|quarterly)\\s+(report|data|metrics|analytics)\\b"
    example: "Weekly Performance Report", "Daily Data Export"

  - regex: "\\bperformance\\s+(report|data|export|metrics)\\b"
    example: "Performance Report - January 2026"

  - regex: "\\b(Q[1-4]|\\d{4})\\s+(results|report|data)\\b"
    example: "Q1 Results", "2026 Report"

  - regex: "\\bmedia\\s+(plan|report|data|metrics)\\b"
    example: "Media Report - Week 3"

  - regex: "\\b(campaign|placement|partner)\\s+report\\b"
    example: "Campaign Report"

  # Explicit data delivery
  - contains: "data delivery"
  - contains: "analytics report"
  - contains: "metrics export"
  - contains: "performance export"
```

### Medium Confidence (score += 0.15)

```yaml
medium_confidence_subjects:
  - contains: "attached"
  - contains: "export"
  - contains: "summary"
  - contains: "numbers"
  - contains: "results"

  - regex: "\\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\\s+\\d{4}\\b"
    example: "Jan 2026 Summary"

  - regex: "\\bweek\\s*(of|ending)?\\s*\\d"
    example: "Week of 1/15", "Week Ending 01-20"
```

### Negative Patterns (skip email)

```yaml
skip_subjects:
  - regex: "^(re:|fwd:|fw:)\\s*re:"  # Deep reply chains
  - contains: "out of office"
  - contains: "automatic reply"
  - contains: "unsubscribe"
  - contains: "calendar"
  - contains: "meeting"
  - contains: "invitation"
  - regex: "\\b(invoice|payment|billing)\\b"  # Financial, not data
```

---

## Body Text Patterns

### Data Delivery Phrases (score += 0.20)

```yaml
delivery_phrases:
  high_confidence:
    - "please find attached"
    - "attached please find"
    - "attached is the"
    - "here is the data"
    - "here is the report"
    - "here are the numbers"
    - "as requested"
    - "as discussed"
    - "for your review"
    - "latest numbers"
    - "updated report"
    - "this week's data"
    - "this month's report"

  medium_confidence:
    - "see attached"
    - "attached file"
    - "data attached"
    - "report attached"
    - "let me know if you have questions"
    - "let me know if you need anything else"
```

### Metric Mentions (score += 0.10)

```yaml
metric_keywords:
  # Standard metrics
  - regex: "\\b(impressions?|imps?)\\b"
  - regex: "\\b(clicks?|click-through)\\b"
  - regex: "\\b(spend|cost|budget)\\b"
  - regex: "\\b(conversions?|converts?)\\b"
  - regex: "\\b(views?|video\\s*views?)\\b"
  - regex: "\\b(reach|frequency)\\b"
  - regex: "\\b(engagement|interactions?)\\b"

  # Rate metrics
  - regex: "\\b(CPM|CPC|CPA|CPV|CPCV)\\b"
  - regex: "\\b(CTR|VTR|CVR)\\b"
  - regex: "\\b(completion\\s*rate|view\\s*rate)\\b"

  # Performance language
  - regex: "\\b(performance|pacing|delivery)\\b"
  - regex: "\\b(over-?deliver|under-?deliver)\\b"
```

### Negative Body Patterns

```yaml
skip_body_patterns:
  - regex: "\\bthis\\s+email\\s+(was\\s+)?sent\\s+automatically\\b"
  - contains: "do not reply"
  - contains: "unsubscribe"
  - regex: "\\bmailer-daemon\\b"
  - regex: "\\bdelivery\\s+(failed|failure|status)\\b"  # Bounce emails
```

---

## Attachment Patterns

### Data File Extensions (score += 0.30)

```yaml
data_extensions:
  high_confidence:
    - ".csv"    # Comma-separated values
    - ".xlsx"   # Excel (modern)
    - ".xls"    # Excel (legacy)
    - ".tsv"    # Tab-separated values

  medium_confidence:
    - ".json"   # JSON data
    - ".xml"    # XML data
    - ".txt"    # May contain data

  requires_inspection:
    - ".pdf"    # May contain tables
    - ".zip"    # May contain data files
    - ".gz"     # Compressed data
```

### Filename Patterns (additional scoring)

```yaml
data_filenames:
  high_confidence:
    - regex: "(report|data|export|metrics|analytics)"
    - regex: "(weekly|daily|monthly|quarterly)"
    - regex: "\\d{4}[-_]\\d{2}[-_]\\d{2}"  # Date in filename
    - regex: "(Q[1-4]|q[1-4])[-_]?\\d{4}"  # Quarter notation

  partner_indicators:
    - regex: "^[A-Z][a-z]+[-_](report|data)"  # PartnerName_report
```

### Skip Attachments

```yaml
skip_attachments:
  - regex: "\\.(jpg|jpeg|png|gif|bmp|svg)$"  # Images (unless specified)
  - regex: "\\.(doc|docx)$"  # Word docs (usually not data)
  - regex: "\\.(ppt|pptx)$"  # Presentations
  - regex: "^signature\\."   # Email signature images
  - regex: "^logo\\."        # Logo images
  - regex: "^image\\d+\\."   # Generic inline images
```

---

## Link Patterns

### Data Source Links (score += 0.20)

```yaml
data_links:
  google_sheets:
    pattern: "docs\\.google\\.com/spreadsheets/d/([a-zA-Z0-9_-]+)"
    extract: "sheet_id"
    confidence: 0.9

  dropbox:
    pattern: "(dropbox\\.com/s/[a-zA-Z0-9]+|dl\\.dropboxusercontent\\.com)"
    confidence: 0.8

  box:
    pattern: "(box\\.com/s/[a-zA-Z0-9]+|app\\.box\\.com/s/[a-zA-Z0-9]+)"
    confidence: 0.8

  onedrive:
    pattern: "(1drv\\.ms/|onedrive\\.live\\.com)"
    confidence: 0.7

  sharepoint:
    pattern: "\\.sharepoint\\.com/.+\\.(xlsx|csv|xls)"
    confidence: 0.8

  s3_presigned:
    pattern: "s3[.-][a-z0-9-]+\\.amazonaws\\.com.*X-Amz-Signature"
    confidence: 0.85
    note: "Check expiration before processing"

  gcs_signed:
    pattern: "storage\\.googleapis\\.com.*X-Goog-Signature"
    confidence: 0.85
```

### Skip Links

```yaml
skip_links:
  - pattern: "(youtube|vimeo|dailymotion)\\.com"
  - pattern: "(twitter|facebook|linkedin|instagram)\\.com"
  - pattern: "unsubscribe"
  - pattern: "mailto:"
  - pattern: "(terms|privacy|policy)"
```

---

## Inline Table Detection

### HTML Table Patterns

```yaml
html_tables:
  detection:
    - tag: "<table"
      min_rows: 2
      min_cols: 2

  data_indicators:
    - header_patterns: ["date", "campaign", "impressions", "clicks", "spend"]
    - numeric_columns: ">= 50% of cells are numbers"
    - consistent_structure: "all rows have same column count"

  skip_tables:
    - contains_only: ["signature", "footer", "header"]
    - row_count: "< 2"
    - is_layout_table: true  # Wide colspan, nested tables
```

### ASCII Table Patterns

```yaml
ascii_tables:
  delimiters:
    - "|"      # Pipe-delimited
    - "\t"     # Tab-delimited
    - ","      # Comma-delimited (in body)

  detection:
    - consistent_delimiter_count: "same count per line for 3+ lines"
    - aligned_columns: "whitespace alignment detected"
    - header_separator: "---" or "===" line present

  min_requirements:
    - lines: 3
    - columns: 2
```

---

## Sender Classification

### Partner Domain Indicators

```yaml
partner_domains:
  high_confidence:
    - known_partner_domains[]  # From configuration
    - regex: "(analytics|reports|data)@"  # Automated sender

  medium_confidence:
    - regex: "@[a-z]+-(media|ads|digital|marketing)\\."
    - regex: "@(adserver|trafficking|ops)\\."

  low_confidence:
    - corporate_domains: true  # Not personal email
    - has_mx_record: true
```

### Skip Senders

```yaml
skip_senders:
  automated:
    - regex: "^(noreply|no-reply|donotreply)@"
    - regex: "^(mailer-daemon|postmaster)@"
    - regex: "@.*\\.calendar\\."

  personal_domains:
    - "@gmail.com"       # Unless in known_contacts
    - "@yahoo.com"
    - "@hotmail.com"
    - "@outlook.com"     # Personal outlook, not business

  known_spam:
    - blocklist[]  # From configuration
```

---

## Combined Scoring Algorithm

```python
def classify_email(email):
    score = 0.0
    factors = []

    # Subject analysis
    subject_score, subject_factors = analyze_subject(email.subject)
    score += subject_score
    factors.extend(subject_factors)

    # Body analysis
    body_score, body_factors = analyze_body(email.body)
    score += body_score
    factors.extend(body_factors)

    # Attachment analysis
    attachment_score, attachment_factors = analyze_attachments(email.attachments)
    score += attachment_score
    factors.extend(attachment_factors)

    # Link analysis
    link_score, link_factors = analyze_links(email.body)
    score += link_score
    factors.extend(link_factors)

    # Sender analysis
    sender_score, sender_factors = analyze_sender(email.from_address)
    score += sender_score
    factors.extend(sender_factors)

    # Inline table detection
    if contains_inline_tables(email.body):
        score += 0.15
        factors.append("inline_table_detected")

    # Apply adjustments
    if is_reply_chain(email):
        score -= 0.10
        factors.append("reply_chain_penalty")

    if is_forwarded(email):
        score -= 0.15
        factors.append("forwarded_penalty")

    if is_known_partner_sender(email.from_address):
        score += 0.15
        factors.append("known_partner_bonus")

    # Normalize
    final_score = max(0.0, min(1.0, score))

    return {
        "score": final_score,
        "classification": classify_by_threshold(final_score),
        "factors": factors
    }

def classify_by_threshold(score):
    if score >= 0.7:
        return "DATA_EMAIL_HIGH_CONFIDENCE"
    elif score >= 0.5:
        return "DATA_EMAIL_MEDIUM_CONFIDENCE"
    elif score >= 0.3:
        return "UNCERTAIN_REVIEW"
    else:
        return "NOT_DATA"
```

---

## Pattern Registry Schema

```yaml
# Example partner patterns for auto-processing
patterns:
  - partner_name: "PartnerA"
    sender_patterns:
      - "*@partnera.com"
      - "reports@partnera-analytics.com"
    subject_patterns:
      - regex: "PartnerA\\s+(Weekly|Daily|Monthly)"
      - contains: "PartnerA Performance"
    expected_format: "xlsx"
    expected_columns:
      - "Date"
      - "Campaign Name"
      - "Placement"
      - "Impressions"
      - "Clicks"
      - "Spend"
    auto_process: true
    confidence_threshold: 0.8
    notes: "PartnerA sends weekly reports every Monday"

  - partner_name: "PartnerB"
    sender_patterns:
      - "*@partnerb.io"
      - "data@partnerb.io"
    subject_patterns:
      - regex: "(Daily|Weekly)\\s+Export"
    expected_format: "csv"
    expected_columns:
      - "date"
      - "campaign_name"
      - "imps"
      - "clicks"
      - "cost"
    column_aliases:
      "imps": "impressions"
      "cost": "spend"
    auto_process: true
    confidence_threshold: 0.85

  - partner_name: "PartnerC"
    sender_patterns:
      - "*@partnerc.com"
    delivery_method: "google_sheets_link"
    link_pattern: "docs.google.com/spreadsheets"
    auto_process: false  # Requires manual auth
    notes: "PartnerC shares Google Sheets links, require access grant"
```

---

## Testing Patterns

### Test Cases

```yaml
test_emails:
  - name: "Clear data email"
    from: "reports@partnera.com"
    subject: "PartnerA Weekly Performance Report"
    body: "Hi, please find attached this week's performance data."
    attachments: ["partnera_weekly_2026-01-20.xlsx"]
    expected_classification: "DATA_EMAIL_HIGH_CONFIDENCE"
    expected_score_min: 0.85

  - name: "Link-based delivery"
    from: "data@partnerb.io"
    subject: "Daily Export - Jan 20"
    body: "Here is today's data: https://docs.google.com/spreadsheets/d/abc123"
    attachments: []
    expected_classification: "DATA_EMAIL_HIGH_CONFIDENCE"
    expected_score_min: 0.75

  - name: "Ambiguous email"
    from: "john@unknown-company.com"
    subject: "Numbers"
    body: "Attached are the numbers you requested."
    attachments: ["report.csv"]
    expected_classification: "UNCERTAIN_REVIEW"
    expected_score_range: [0.3, 0.6]

  - name: "Not a data email"
    from: "colleague@company.com"
    subject: "Re: Meeting tomorrow"
    body: "Sure, let's meet at 3pm."
    attachments: []
    expected_classification: "NOT_DATA"
    expected_score_max: 0.2

  - name: "Out of office"
    from: "partner@partnera.com"
    subject: "Out of Office: Re: Weekly Report"
    body: "I am currently out of the office..."
    attachments: []
    expected_classification: "NOT_DATA"
    expected_score_max: 0.1
```
