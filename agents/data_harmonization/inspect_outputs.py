#!/usr/bin/env python3
"""
Inspect Stage 1 outputs in detail.
Shows actual data, column names, and sheet tab information.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stages.stage1_ingestion import SourceIngestion
from models.schemas import RawSource
from utils.config_loader import load_config

# Google Sheets API imports
from googleapiclient.discovery import build
import google.auth


def inspect_sheets_tabs(sheet_id: str):
    """List all available tabs in a Google Sheet."""
    print("\n" + "="*80)
    print("GOOGLE SHEETS TAB INSPECTION")
    print("="*80)

    try:
        creds, _ = google.auth.default(
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
        )

        service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
        sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()

        sheets = sheet_metadata.get('sheets', [])

        print(f"\nSpreadsheet: {sheet_metadata.get('properties', {}).get('title', 'Unknown')}")
        print(f"Sheet ID: {sheet_id}")
        print(f"\nAvailable tabs ({len(sheets)}):\n")

        for i, sheet in enumerate(sheets, 1):
            props = sheet.get('properties', {})
            sheet_id_gid = props.get('sheetId', 'N/A')
            title = props.get('title', 'Untitled')
            row_count = props.get('gridProperties', {}).get('rowCount', 'N/A')
            col_count = props.get('gridProperties', {}).get('columnCount', 'N/A')

            print(f"{i}. {title}")
            print(f"   GID: {sheet_id_gid}")
            print(f"   Size: {row_count} rows × {col_count} columns")
            print()

    except Exception as e:
        print(f"Error inspecting sheets: {e}")


def inspect_stage1_output(source_name: str, source: RawSource):
    """Inspect Stage 1 ingestion output in detail."""
    print("\n" + "="*80)
    print(f"STAGE 1 OUTPUT: {source_name}")
    print("="*80)

    config = load_config()
    ingestion = SourceIngestion(config)

    try:
        df, metadata = ingestion.ingest(source)

        print(f"\nSource: {source.source_system}")
        print(f"Location: {source.source_location}")

        # Show metadata
        print("\n" + "-"*80)
        print("INGESTION METADATA")
        print("-"*80)
        print(f"Rows read: {metadata.rows_read}")
        print(f"Columns read: {metadata.columns_read}")
        print(f"Encoding: {metadata.encoding}")
        print(f"Header row: {metadata.header_row}")
        print(f"Metadata rows skipped: {metadata.metadata_rows_skipped}")

        if metadata.warnings:
            print(f"\nWarnings ({len(metadata.warnings)}):")
            for warning in metadata.warnings:
                print(f"  - {warning}")

        # Show DataFrame info
        print("\n" + "-"*80)
        print("DATAFRAME INFO")
        print("-"*80)
        print(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"\nColumn names ({len(df.columns)}):")
        for i, col in enumerate(df.columns, 1):
            try:
                series = df.loc[:, col]  # Use .loc to select column
                col_type = str(series.dtype)
                null_count = int(series.isnull().sum())
                null_pct = (null_count / len(df) * 100) if len(df) > 0 else 0
                col_repr = repr(col) if col is not None else 'None'
                print(f"{i:2}. [{col_type:10}] {col_repr[:45]:47} (nulls: {null_count}/{len(df)} = {null_pct:.1f}%)")
            except Exception as e:
                print(f"{i:2}. [ERROR] {col!r:47} (error: {e})")

        # Show actual data
        print("\n" + "-"*80)
        print("FIRST 5 ROWS")
        print("-"*80)
        print(df.head(5).to_string())

        print("\n" + "-"*80)
        print("DATA TYPES & SAMPLE VALUES")
        print("-"*80)
        for col in df.columns:
            print(f"\n{col!r}:")
            print(f"  Type: {df[col].dtype}")
            print(f"  Non-null: {df[col].count()}/{len(df)}")
            print(f"  Unique values: {df[col].nunique()}")

            # Show sample non-null values
            non_null_values = df[col].dropna().unique()[:5]
            if len(non_null_values) > 0:
                print(f"  Samples: {list(non_null_values)}")

        print("\n" + "="*80)
        print(f"✅ {source_name} inspection complete!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Error ingesting {source_name}: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Inspect all test sources."""

    # Load email input files
    email_dir = Path("/Users/eugenetsenter/gh_projects/email/first-party-data/inputs")

    jck_input = email_dir / "19b99197d733c22b_input.json"
    natl_jeweler_input = email_dir / "19b992f5ebb65262_input.json"

    print("\n" + "="*80)
    print("STAGE 1: SOURCE INGESTION - DETAILED OUTPUT INSPECTION")
    print("="*80)

    # Test 1: JCK Excel Attachment
    with open(jck_input) as f:
        jck_data = json.load(f)

    # Find the Excel attachment from raw_sources
    jck_attachment = [s for s in jck_data['raw_sources'] if s['source_system'] == 'email_attachment'][0]
    jck_source = RawSource(
        source_system=jck_attachment['source_system'],
        source_location=jck_attachment['source_location'],
        data_type=jck_attachment.get('data_type', 'xlsx')
    )

    inspect_stage1_output("JCK Report (Excel Attachment)", jck_source)

    # Test 2: National Jeweler Google Sheets
    with open(natl_jeweler_input) as f:
        natl_data = json.load(f)

    # Find Google Sheets link from raw_sources
    sheets_source = [s for s in natl_data['raw_sources'] if s['source_system'] == 'google_sheets'][0]
    sheets_link = sheets_source['source_location']
    sheet_id = sheets_link.split('/d/')[1].split('/')[0]

    # First, inspect what tabs are available
    inspect_sheets_tabs(sheet_id)

    # Then ingest with gid=0 (what we're currently doing)
    natl_source = RawSource(
        source_system='google_sheets',
        source_location=sheets_link,
        data_type='google_sheets'
    )

    inspect_stage1_output("National Jeweler (Google Sheets - Auto-selected tab)", natl_source)

    print("\n" + "="*80)
    print("Which tab should we use instead?")
    print("="*80)
    print("\nLet me know the correct tab name or GID, and I'll update the ingestion.")


if __name__ == "__main__":
    main()
