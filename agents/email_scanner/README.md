# Email Scanner Agent

## Role

The Email Scanner Agent monitors Gmail for first-party data deliveries from partners. It identifies emails containing data files (CSV, Excel, etc.) or data links (Google Sheets, Dropbox), and outputs structured JSON for the Data Harmonization pipeline.

## Position in Pipeline

```
┌─────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Gmail     │────▶│   Email Scanner     │────▶│ Data Harmonization  │
│   Inbox     │     │       Agent         │     │       Agent         │
└─────────────┘     └─────────────────────┘     └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  scan_results/*.json │
                    └─────────────────────┘
```

## Quick Start

```bash
# Scan last 7 days
python scan_for_data.py --days 7

# Filter by partner
python scan_for_data.py --partner "PartnerA"

# Combine filters
python scan_for_data.py --days 7 --partner "PartnerA"

# Download attachments too
python scan_for_data.py --days 7 --save-attachments
```

Uses the same Gmail OAuth token as `generate_markdown_summary.py` (`~/.cache/gmail_token.pickle`).

## Command Line Options

```
-d, --days N          Days to look back (default: 7)
-a, --after DATE      Start date YYYY/MM/DD (overrides --days)
-b, --before DATE     End date YYYY/MM/DD
-p, --partner NAME    Filter by partner name (searches sender & subject)
--has-attachment      Only emails with data file attachments
--data-keywords       Only emails with data-related keywords in subject
--save-attachments    Download and save data file attachments
-o, --output FILE     Output JSON path
```

## Output

Results are saved to `scan_results/scan_TIMESTAMP.json`:

```json
{
  "scan_metadata": {
    "scan_time": "2026-01-21T10:30:00",
    "after": "2026/01/14",
    "before": "2026/01/22",
    "partner_filter": null,
    "total_emails_scanned": 47,
    "emails_after_filtering": 35,
    "emails_with_data": 5
  },
  "data_emails": [...],
  "all_emails": [...]
}
```

Each email record includes:
- Sender, subject, date, snippet
- Attachments with metadata (filename, size, is_data_file)
- Data links detected (Google Sheets, Dropbox, Box, OneDrive)
- Gmail permalink

## Supported Data Types

**Attachments:** `.csv`, `.xlsx`, `.xls`, `.tsv`, `.json`, `.xml`

**Links:** Google Sheets, Dropbox, Box, OneDrive

## Design Documentation

For the full agent design (not yet implemented):

| Document | Description |
|----------|-------------|
| [AGENT_DESIGN.md](./AGENT_DESIGN.md) | Full technical design with pipeline stages |
| [DETECTION_PATTERNS.md](./DETECTION_PATTERNS.md) | Pattern matching rules and scoring |
| [Contract](../../schemas/contracts/email_scanner_contract.md) | Input/output contract spec |

## Downstream Consumer

The **Data Harmonization Agent** consumes the `data_emails` from the scan output.
