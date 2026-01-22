"""
Test Stage 1 Ingestion with real FPD data from emails.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stages.stage1_ingestion import SourceIngestion
from models import RawSource
from utils import load_config


def test_email_attachment():
    """Test ingesting from email attachment (JCK Excel file)."""
    print("=" * 80)
    print("TEST 1: Email Attachment (Excel file)")
    print("=" * 80)
    print()

    # Load the input JSON
    input_path = "/Users/eugenetsenter/gh_projects/email/first-party-data/inputs/19b99197d733c22b_input.json"
    with open(input_path, 'r') as f:
        input_data = json.load(f)

    # Get the attachment source
    attachment_source = None
    for source in input_data['raw_sources']:
        if source['source_system'] == 'email_attachment':
            attachment_source = RawSource(**source)
            break

    if not attachment_source:
        print("No email attachment found in input")
        return

    # Initialize ingestion
    config = load_config()
    ingestion = SourceIngestion(config)

    # Ingest
    print(f"Source: {attachment_source.source_system}")
    print(f"Location: {attachment_source.source_location}")
    print()

    df, metadata = ingestion.ingest(attachment_source)

    print("Ingestion Results:")
    print(f"  Rows read: {metadata.rows_read}")
    print(f"  Columns read: {metadata.columns_read}")
    print(f"  Encoding: {metadata.encoding}")
    print(f"  Header row: {metadata.header_row}")
    print(f"  Metadata rows skipped: {metadata.metadata_rows_skipped}")
    if metadata.warnings:
        print(f"  Warnings: {metadata.warnings}")
    print()

    print("DataFrame Info:")
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
    print()

    print("Sample Data (first 3 rows):")
    print(df.head(3).to_string())
    print()
    print("✅ Email attachment ingestion successful!")
    print()


def test_google_sheets():
    """Test ingesting from Google Sheets link."""
    print("=" * 80)
    print("TEST 2: Google Sheets Link")
    print("=" * 80)
    print()

    # Load the National Jeweler input JSON
    input_path = "/Users/eugenetsenter/gh_projects/email/first-party-data/inputs/19b992f5ebb65262_input.json"
    with open(input_path, 'r') as f:
        input_data = json.load(f)

    # Get the Google Sheets source
    sheets_source = None
    for source in input_data['raw_sources']:
        if source['source_system'] == 'google_sheets':
            sheets_source = RawSource(**source)
            break

    if not sheets_source:
        print("No Google Sheets source found in input")
        return

    # Initialize ingestion
    config = load_config()
    ingestion = SourceIngestion(config)

    # Ingest
    print(f"Source: {sheets_source.source_system}")
    print(f"Location: {sheets_source.source_location}")
    print()

    try:
        df, metadata = ingestion.ingest(sheets_source)

        print("Ingestion Results:")
        print(f"  Rows read: {metadata.rows_read}")
        print(f"  Columns read: {metadata.columns_read}")
        print(f"  Encoding: {metadata.encoding}")
        if metadata.warnings:
            print(f"  Warnings: {metadata.warnings}")
        print()

        print("DataFrame Info:")
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {list(df.columns)}")
        print()

        print("Sample Data (first 3 rows):")
        print(df.head(3).to_string())
        print()
        print("✅ Google Sheets ingestion successful!")
        print()

    except Exception as e:
        print(f"⚠️  Google Sheets ingestion failed: {str(e)}")
        print("   (This is expected if sheet is not publicly accessible)")
        print()


def test_both_sources():
    """Test processing both sources from the same campaign."""
    print("=" * 80)
    print("TEST 3: Processing Multiple Data Sources")
    print("=" * 80)
    print()

    # Load both input JSONs
    jck_path = "/Users/eugenetsenter/gh_projects/email/first-party-data/inputs/19b99197d733c22b_input.json"
    nj_path = "/Users/eugenetsenter/gh_projects/email/first-party-data/inputs/19b992f5ebb65262_input.json"

    with open(jck_path, 'r') as f:
        jck_input = json.load(f)

    with open(nj_path, 'r') as f:
        nj_input = json.load(f)

    print("Email 1: JCK Report")
    print(f"  Subject: {jck_input['source_email']['subject']}")
    print(f"  From: {jck_input['source_email']['from']}")
    print(f"  Sources: {len(jck_input['raw_sources'])}")
    for source in jck_input['raw_sources']:
        print(f"    - {source['source_system']}: {source['data_type']}")
    print()

    print("Email 2: National Jeweler Report")
    print(f"  Subject: {nj_input['source_email']['subject']}")
    print(f"  From: {nj_input['source_email']['from']}")
    print(f"  Sources: {len(nj_input['raw_sources'])}")
    for source in nj_input['raw_sources']:
        print(f"    - {source['source_system']}: {source['data_type']}")
    print()

    print("Both emails are part of the ADIF campaign!")
    print("JCK = RX Global/Reed Exhibitions (partner_id: par_relx)")
    print("National Jeweler = Also published by JCK/Reed Exhibitions")
    print()

    config = load_config()
    ingestion = SourceIngestion(config)

    # Process JCK
    print("Processing JCK attachment...")
    jck_source = RawSource(**jck_input['raw_sources'][0])
    df_jck, meta_jck = ingestion.ingest(jck_source)
    print(f"  ✓ Loaded {len(df_jck)} rows from JCK")
    print()

    # Try National Jeweler
    print("Processing National Jeweler Google Sheet...")
    try:
        nj_source = RawSource(**nj_input['raw_sources'][0])
        df_nj, meta_nj = ingestion.ingest(nj_source)
        print(f"  ✓ Loaded {len(df_nj)} rows from National Jeweler")
        print()
        print(f"Total data sources successfully ingested: 2")
    except Exception as e:
        print(f"  ⚠️  Could not load National Jeweler: {str(e)}")
        print(f"  Total data sources successfully ingested: 1")
    print()


if __name__ == "__main__":
    print()
    print("🚀 Testing Stage 1: Source Ingestion")
    print("=" * 80)
    print()

    try:
        test_email_attachment()
        test_google_sheets()
        test_both_sources()

        print("=" * 80)
        print("✅ All Stage 1 tests completed!")
        print("=" * 80)
        print()

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
