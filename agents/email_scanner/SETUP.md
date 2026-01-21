```

```
# Email Scanner Agent - Setup Guide

## Prerequisites

- Python 3.10+
- Gmail account with API access enabled
- Google Cloud project with Gmail API enabled

## Installation

### 1. Install Dependencies

```bash
cd agents/email_scanner
pip install -r requirements.txt
```

### 2. Set Up Google Cloud Credentials

The Email Scanner uses the same OAuth2 authentication as `generate_markdown_summary.py`.

#### Option A: Use Existing Token

If you've already run `generate_markdown_summary.py` and authenticated, the token is cached at:
```
~/.cache/gmail_token.pickle
```

The Email Scanner will automatically use this token.

#### Option B: New Setup

1. **Create a Google Cloud Project** (if you don't have one)
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable the Gmail API**
   - Navigate to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click "Enable"

3. **Create OAuth 2.0 Credentials**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Select "Desktop app" as the application type
   - Download the JSON file

4. **Save the Credentials**

   Place the downloaded JSON file in one of these locations:
   ```
   ./credentials.json           # Project root
   ~/credentials.json           # Home directory
   ~/.secrets/credentials.json  # Secrets directory
   ```

5. **First Run - Browser Authentication**

   The first time you run the scanner, it will:
   - Open a browser window for Google OAuth consent
   - Ask you to authorize Gmail read access
   - Cache the token to `~/.cache/gmail_token.pickle`

## Usage

### Basic Scan

```bash
# Scan yesterday's emails
python -m agents.email_scanner.src.run_scan

# Scan last 7 days
python -m agents.email_scanner.src.run_scan --days 7

# Scan specific date range
python -m agents.email_scanner.src.run_scan --after 2026/01/15 --before 2026/01/21
```

### With Partner Patterns

Create a patterns file (`patterns.json`):

```json
{
  "patterns": [
    {
      "partner_name": "PartnerA",
      "sender_patterns": ["*@partnera.com", "reports@partnera-analytics.com"],
      "subject_patterns": ["PartnerA Weekly", "PartnerA Performance"],
      "expected_format": "xlsx",
      "expected_columns": ["Date", "Campaign Name", "Impressions", "Clicks", "Spend"],
      "auto_process": true,
      "confidence_threshold": 0.8
    }
  ]
}
```

Then run:

```bash
python -m agents.email_scanner.src.run_scan --days 7 --patterns patterns.json
```

### Output

Results are saved to `agents/email_scanner/scan_results/` by default:

```
scan_results/
├── es-20260121-083000.json     # Scan results
└── extracts/
    └── es-20260121-083000/     # Extracted attachments
        ├── report.xlsx
        └── data.csv
```

### Command Line Options

```
-d, --days N         Days to scan back (default: 1)
-a, --after DATE     Start date YYYY/MM/DD
-b, --before DATE    End date YYYY/MM/DD
-c, --category CAT   Gmail category (default: primary)
--max-emails N       Maximum emails to process (default: 100)
-p, --patterns FILE  Path to partner patterns JSON
-o, --output DIR     Output directory
--dry-run            Classify only, don't extract attachments
-v, --verbose        Enable debug logging
```

## Programmatic Usage

```python
from datetime import datetime, timedelta
from agents.email_scanner.src import (
    create_gmail_client,
    EmailScanner,
    PartnerPattern,
)

# Create Gmail client (uses cached token)
gmail = create_gmail_client()

# Define known partner patterns
patterns = [
    PartnerPattern(
        partner_name="PartnerA",
        sender_patterns=["*@partnera.com"],
        subject_patterns=["Weekly Report"],
        auto_process=True,
    ),
]

# Create scanner
scanner = EmailScanner(
    gmail_client=gmail,
    patterns=patterns,
    extraction_dir="/tmp/extracts",
)

# Run scan
results = scanner.scan(
    since=datetime.now() - timedelta(days=7),
    max_results=50,
)

# Process results
for payload in results['auto_processed']:
    print(f"Auto-processing: {payload['partner_name']}")
    # Send to Data Harmonization Agent...

for item in results['review_queue']:
    print(f"Needs review: {item['email_summary']['subject']}")
```

## Integration with Data Harmonization Agent

The `auto_processed` payloads are formatted for direct input to the Data Harmonization Agent:

```python
# From scan results
for payload in results['auto_processed']:
    # Each payload contains 'raw_sources' ready for harmonization
    raw_sources = payload['raw_sources']

    # Send to Data Harmonization Agent
    harmonization_input = {
        "raw_sources": raw_sources,
        "run_config": {
            "run_id": f"dh-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "dry_run": False,
        }
    }
```

## Troubleshooting

### "No credentials.json found"

Download OAuth credentials from Google Cloud Console and save to one of the expected paths.

### "Token expired" or authentication issues

Delete the cached token and re-authenticate:
```bash
rm ~/.cache/gmail_token.pickle
python -m agents.email_scanner.src.run_scan --days 1
```

### "Access denied" or scope issues

The scanner requires `gmail.readonly` scope. If you previously authorized with different scopes, delete the token and re-authenticate.

### Rate limiting

If you hit Gmail API rate limits:
- Reduce `--max-emails`
- Add delays between scans
- Check [Gmail API quotas](https://developers.google.com/gmail/api/reference/quota)

## Environment Variables

Optional environment variables (can also be set in `.env`):

```bash
# Custom token location
GMAIL_TOKEN_FILE=~/.config/gmail_token.pickle

# Logging level
LOG_LEVEL=DEBUG
```
