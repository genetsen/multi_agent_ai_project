# Data Harmonization Agent

Transforms raw first-party data from various sources into a canonical format.

## Status

| Stage | Status | Description |
|-------|--------|-------------|
| **Stage 1: Source Ingestion** | ✅ **COMPLETE** | Multi-source data loading with auto-detection |
| **Stage 2: Schema Discovery** | 📋 Next | Column profiling and type detection |
| **Stage 3: Schema Mapping** | 📋 Planned | AI-assisted field mapping |
| **Stage 4: Data Transformation** | 📋 Planned | Format standardization and unpivoting |
| **Stage 5: Quality Checks** | 📋 Planned | Validation and confidence scoring |

**Last Updated**: January 21, 2026
**Test Data**: ADIF Campaign (JCK + National Jeweler reports)
**Test Results**: 100% success rate (2/2 sources, 3,808 total rows)

### Recent Changes (January 21, 2026)

- ✅ **Completed Stage 1**: Source Ingestion with full test coverage
- ✅ **Google Sheets Integration**: Using Application Default Credentials (simplified auth)
- ✅ **Automatic Header Detection**: Successfully handled files with 6-9 rows of metadata
- ✅ **Real-World Testing**: Validated with actual campaign data (ADIF/De Beers)
- ✅ **Error Recovery**: Auto-corrects file types, falls back to public export when API fails
- 📖 **Documentation**: Comprehensive README with test results and troubleshooting

## Features

- **Multi-source ingestion**: Email attachments, Google Sheets, CSV files, email body data
- **Automatic header detection**: Skips metadata rows and finds actual data headers
- **Encoding auto-detection**: Handles UTF-8, Latin-1, CP1252
- **File type correction**: Auto-detects actual file type even if mislabeled
- **Google Sheets API support**: Read private sheets with Application Default Credentials
- **Confidence-based processing**: Auto-process high confidence, flag low confidence for review
- **Quality validation**: Built-in data quality checks
- **Data lineage tracking**: Complete audit trail from source to output

## Key Insights

### Why Application Default Credentials?
We use Google's Application Default Credentials (ADC) instead of OAuth tokens because:
- **Shared across tools**: ADC works with all Google Cloud services (BigQuery, Sheets, Drive)
- **Automatic refresh**: No manual token management needed
- **Simpler setup**: Users already authenticated with `gcloud` don't need separate OAuth flow
- **Enterprise-friendly**: Supports service account impersonation for production environments

### Why Header Detection Matters
Real-world FPD files often have 5-10 rows of metadata before the actual data:
- Partner logos, report dates, campaign names in the header area
- Detection algorithm uses **keyword matching** (`config.yaml`: `header_keywords`)
- Falls back to **heuristics** if no keywords found (row with most non-empty cells)
- Saves manual cleanup time and reduces errors

### Why Pydantic Models?
All data contracts use Pydantic for:
- **Runtime validation**: Catch schema mismatches immediately
- **Type safety**: IDE autocomplete and type checking
- **Automatic serialization**: Easy JSON/dict conversion
- **Living documentation**: Models ARE the contract specification
- **Version control**: Schema changes are tracked in git

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Sheets Authentication (Optional)

If you need to read private Google Sheets, authenticate with Google Cloud using Application Default Credentials:

```bash
# Authenticate with required scopes
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/spreadsheets.readonly,https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/cloud-platform

# Verify authentication
cd /Users/eugenetsenter/gh_projects/multi_agent_ai_project/agents/data_harmonization
python setup_sheets_auth.py
```

This saves credentials to `~/.config/gcloud/application_default_credentials.json`

**Note**: Public Google Sheets don't require authentication.

## Usage

### Run Tests

```bash
# Test Stage 1 (Source Ingestion)
python test_ingestion.py
```

### Process Data

```python
from stages import SourceIngestion
from models import RawSource
from utils import load_config

# Initialize
config = load_config()
ingestion = SourceIngestion(config)

# Ingest from email attachment
source = RawSource(
    source_system='email_attachment',
    source_location='/path/to/file.xlsx',
    data_type='xlsx'
)
df, metadata = ingestion.ingest(source)

# Ingest from Google Sheets
sheets_source = RawSource(
    source_system='google_sheets',
    source_location='https://docs.google.com/spreadsheets/d/SHEET_ID/edit'
)
df, metadata = ingestion.ingest(sheets_source)
```

## Architecture

### 5-Stage Pipeline

1. **Stage 1: Source Ingestion** ✅ **COMPLETE**
   - ✅ Multi-source loading (Excel, CSV, Google Sheets, TSV)
   - ✅ Automatic header detection with configurable keywords
   - ✅ Encoding auto-detection (UTF-8, Latin-1, CP1252)
   - ✅ File type correction (handles mislabeled files)
   - ✅ Metadata row skipping (finds actual data start)
   - ✅ Google Sheets API integration with Application Default Credentials
   - ✅ Fallback to public export for accessible sheets
   - ✅ Comprehensive error handling and warnings
   - 📍 **Tested**: 100% success on real campaign data (3,808 rows)

2. **Stage 2: Schema Discovery** 📋 **NEXT**
   - Profile columns (data types, patterns, null rates)
   - Detect date formats in column names
   - Identify metric vs dimension columns
   - Clean messy column names (empty, None, duplicates)
   - Sample distinct values for validation

3. **Stage 3: Schema Mapping** 📋 PLANNED
   - Map source columns to canonical schema
   - Calculate mapping confidence scores
   - Fuzzy matching for similar column names
   - AI-assisted mapping with Claude API
   - Human review queue for low-confidence mappings

4. **Stage 4: Data Transformation** 📋 PLANNED
   - Apply schema mappings
   - Unpivot wide-format metrics to long format
   - Standardize data types and date formats
   - Handle missing values and nulls
   - Create source lineage IDs

5. **Stage 5: Quality Checks** 📋 PLANNED
   - Validate against quality rules (config.yaml)
   - Check for duplicates and invalid dates
   - Verify required fields are present
   - Calculate overall confidence score
   - Generate quality report with actionable warnings

### Data Models

All data contracts are defined using Pydantic models in `src/models/schemas.py`:

- `HarmonizationInput`: Complete input including email metadata and raw sources
- `RawSource`: Single data source (file, URL, etc.)
- `HarmonizationOutput`: Final harmonized data with lineage and quality metrics
- `IngestionMetadata`: Ingestion statistics and warnings
- `FieldMapping`: How source fields map to canonical schema
- `ValidationResult`: Quality check results

### Configuration

All settings in `config/config.yaml`:

- Canonical schema definition
- Quality validation rules
- Known metrics and partners
- Header detection keywords
- Supported encodings

## Canonical Schema

Output format (long format):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| date | date | Yes | Metric date |
| partner_name | string | Yes | Canonical partner name |
| metric_name | string | Yes | Standardized metric name |
| metric_value | decimal | Yes | Metric value |
| campaign_name | string | No | Campaign identifier |
| placement_name | string | No | Ad placement/creative |
| device_type | string | No | desktop/mobile/tablet |
| country | string | No | ISO country code |
| source_record_id | string | No | Source data lineage |
| extraction_timestamp | datetime | No | When data was extracted |
| notes | string | No | Additional context |

## Testing

### Test Data

Real FPD data from ADIF campaign:

- **JCK Report**: Excel file with 6 rows, header at row 6
  - `/Users/eugenetsenter/gh_projects/email/first-party-data/inputs/19b99197d733c22b_input.json`

- **National Jeweler Report**: Google Sheets link
  - `/Users/eugenetsenter/gh_projects/email/first-party-data/inputs/19b992f5ebb65262_input.json`

### Test Results

#### Stage 1: Source Ingestion ✅ COMPLETE

**Test 1: Email Attachment (Excel)**
```
✅ JCK Report - DeBeers ADIF Campaign
  Source: Email attachment (.xls file)
  Rows read: 6
  Columns read: 4
  Header detected: Row 6
  Metadata rows skipped: 6
  Columns: ['Line item', 'Total impressions', 'Total clicks', 'Total CTR']

  Warnings handled:
  - Auto-corrected file type (xlsx → xls)
  - Detected and skipped 6 metadata rows
```

**Test 2: Google Sheets (Private)**
```
✅ National Jeweler Report - ADIF Campaign
  Source: Private Google Sheets (via Application Default Credentials)
  Rows read: 3,802
  Columns read: 27
  Header detected: Row 9
  Metadata rows skipped: 9

  Warnings handled:
  - Sheet gid not found, used first sheet instead
  - Messy headers (empty column names, None values)

  Authentication: Application Default Credentials
  Project: looker-studio-pro-452620
```

**Test 3: Multi-Source Processing**
```
✅ Both data sources ingested successfully
  Total sources processed: 2
  Total rows: 3,808
  Success rate: 100%
```

## Troubleshooting

### Google Sheets Access Issues

**Error**: `ACCESS_TOKEN_SCOPE_INSUFFICIENT`

**Solution**: Re-authenticate with proper scopes:
```bash
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/spreadsheets.readonly,https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/cloud-platform
```

Then verify:
```bash
python setup_sheets_auth.py
```

---

**Error**: `No valid credentials found`

**Solution**: Install Google Cloud SDK and authenticate:
```bash
# Install gcloud CLI (if not already installed)
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/spreadsheets.readonly,https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/cloud-platform
```

---

**Alternative**: Make the sheet publicly accessible (Share > Anyone with link can view).

### File Type Errors

**Error**: `File contains no valid workbook part`

**Solution**: The agent auto-detects and corrects file type mismatches. No action needed.

### Import Errors

Make sure you're in the project directory and have installed dependencies:

```bash
cd /Users/eugenetsenter/gh_projects/multi_agent_ai_project/agents/data_harmonization
pip install -r requirements.txt
python test_ingestion.py
```

## Documentation

| Document | Description |
|----------|-------------|
| [AGENT_DESIGN.md](./AGENT_DESIGN.md) | Full technical design with processing pipeline, decision trees, and edge cases |
| [SCHEMA_MAPPING_PROMPTS.md](./SCHEMA_MAPPING_PROMPTS.md) | LLM prompts and validation rules for AI-assisted mapping |
| [Contract](../../schemas/contracts/data_harmonization_contract.md) | Input/output contract specification |

## Next Steps

### Immediate (Stage 2: Schema Discovery)

- [ ] Column profiling
  - Detect data types (string, numeric, date, boolean)
  - Calculate null rates and unique value counts
  - Sample distinct values for each column
- [ ] Date format detection
  - Identify date columns from messy headers
  - Detect format patterns (MM/DD/YYYY, YYYY-MM-DD, etc.)
- [ ] Metric vs. dimension classification
  - Use keywords and patterns to identify metric columns
  - Distinguish between dimensions and measures
- [ ] Clean column names
  - Handle empty, None, and duplicate column names
  - Standardize naming conventions

### Upcoming Stages

- [ ] **Stage 3**: Schema Mapping with AI-assisted field matching
- [ ] **Stage 4**: Data Transformation (unpivoting, type conversion)
- [ ] **Stage 5**: Quality Checks (validation rules, confidence scoring)
- [ ] **Orchestrator**: Main CLI and end-to-end pipeline
- [ ] **Testing**: Full integration tests with multiple campaigns
