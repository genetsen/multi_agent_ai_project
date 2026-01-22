"""
Stage 1: Source Ingestion

Connects to various data sources and loads raw data into DataFrame.
"""

import pandas as pd
from pathlib import Path
from typing import Tuple, Dict, Any, List
import re

from models import RawSource, IngestionMetadata


class SourceIngestion:
    """Handles ingestion from various data sources."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Source Ingestion stage.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.source_config = config.get('source_handling', {})

    def ingest(self, raw_source: RawSource) -> Tuple[pd.DataFrame, IngestionMetadata]:
        """
        Ingest data from a raw source.

        Args:
            raw_source: RawSource object containing source details

        Returns:
            Tuple of (DataFrame, IngestionMetadata)
        """
        source_system = raw_source.source_system
        source_location = raw_source.source_location

        # Route to appropriate ingestion method
        if source_system in ['email_attachment', 'csv', 'email_body']:
            return self._ingest_file(source_location, raw_source.data_type)
        elif source_system == 'google_sheets':
            return self._ingest_google_sheets(source_location)
        elif source_system == 's3':
            return self._ingest_s3(source_location)
        elif source_system == 'sftp':
            return self._ingest_sftp(source_location)
        elif source_system == 'bigquery':
            return self._ingest_bigquery(source_location)
        else:
            raise ValueError(f"Unsupported source_system: {source_system}")

    def _ingest_file(self, file_path: str, data_type: str = None) -> Tuple[pd.DataFrame, IngestionMetadata]:
        """
        Ingest data from a local file (CSV, Excel, etc.).

        Args:
            file_path: Path to the file
            data_type: Type of file (csv, xlsx, xls)

        Returns:
            Tuple of (DataFrame, IngestionMetadata)
        """
        warnings = []
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size_bytes = path.stat().st_size

        # Always detect file type from actual file extension (override if provided incorrectly)
        actual_extension = path.suffix.lower().replace('.', '')
        if data_type is None or data_type != actual_extension:
            if data_type and data_type != actual_extension:
                warnings.append(f"Provided data_type '{data_type}' doesn't match file extension '{actual_extension}', using '{actual_extension}'")
            data_type = actual_extension

        # Read the file with header detection
        if data_type in ['xlsx', 'xls']:
            df_raw, header_info = self._read_excel_with_header_detection(file_path, data_type)
        elif data_type == 'csv':
            df_raw, header_info = self._read_csv_with_header_detection(file_path)
        else:
            raise ValueError(f"Unsupported data_type: {data_type}")

        metadata = IngestionMetadata(
            rows_read=len(df_raw),
            columns_read=len(df_raw.columns),
            encoding=header_info.get('encoding', 'utf-8'),
            file_size_bytes=file_size_bytes,
            header_row=header_info.get('header_row'),
            metadata_rows_skipped=header_info.get('metadata_rows_skipped', 0),
            warnings=warnings + header_info.get('warnings', [])
        )

        return df_raw, metadata

    def _read_excel_with_header_detection(self, file_path: str, data_type: str) -> Tuple[pd.DataFrame, Dict]:
        """
        Read Excel file with automatic header detection.

        Args:
            file_path: Path to Excel file
            data_type: xlsx or xls

        Returns:
            Tuple of (DataFrame, header_info dict)
        """
        engine = 'openpyxl' if data_type == 'xlsx' else 'xlrd'
        warnings = []

        # First, read without assuming header location
        df_preview = pd.read_excel(file_path, engine=engine, header=None, nrows=20)

        # Detect header row
        header_row = self._detect_header_row(df_preview)

        if header_row is None:
            warnings.append("Could not detect header row, using first row")
            header_row = 0

        if header_row > 0:
            warnings.append(f"Header detected at row {header_row}, skipping {header_row} metadata rows")

        # Read with detected header
        df = pd.read_excel(file_path, engine=engine, skiprows=header_row)

        # Check if first row is actually the header (sometimes it gets read as data)
        if df.iloc[0].astype(str).str.contains('|'.join(self.source_config.get('header_detection', {}).get('keywords', [])), case=False, regex=True).any():
            df.columns = df.iloc[0]
            df = df.iloc[1:].reset_index(drop=True)
            header_row += 1

        # Drop rows that are all NaN
        df = df.dropna(how='all').reset_index(drop=True)

        header_info = {
            'encoding': 'auto-detected',
            'header_row': header_row,
            'metadata_rows_skipped': header_row,
            'warnings': warnings
        }

        return df, header_info

    def _detect_header_row(self, df_preview: pd.DataFrame) -> int:
        """
        Detect which row contains the actual column headers.

        Args:
            df_preview: Preview DataFrame (first ~20 rows)

        Returns:
            Row index of header (0-indexed), or None if not found
        """
        keywords = self.source_config.get('header_detection', {}).get('keywords', [])
        max_rows = self.source_config.get('header_detection', {}).get('max_rows_to_scan', 20)

        for idx in range(min(len(df_preview), max_rows)):
            row = df_preview.iloc[idx]

            # Convert to strings and check for keywords
            row_str = row.astype(str).str.lower()

            # Count keyword matches
            keyword_matches = sum(row_str.str.contains('|'.join(keywords), case=False, regex=True))

            # If we find 2+ keyword matches, likely the header
            if keyword_matches >= 2:
                return idx

            # Also check if row has consistent string types (likely header)
            # while next row has numbers (likely data)
            if idx < len(df_preview) - 1:
                next_row = df_preview.iloc[idx + 1]

                # Count non-null values
                row_non_null = row.notna().sum()
                next_non_null = next_row.notna().sum()

                # If current row is mostly strings and next is mostly numbers
                if row_non_null >= len(row) * 0.5:
                    row_is_strings = sum(isinstance(v, str) for v in row if pd.notna(v))
                    next_is_numbers = sum(isinstance(v, (int, float)) for v in next_row if pd.notna(v))

                    if row_is_strings >= len(row) * 0.5 and next_is_numbers >= len(next_row) * 0.5:
                        return idx

        return None

    def _read_csv_with_header_detection(self, file_path: str) -> Tuple[pd.DataFrame, Dict]:
        """
        Read CSV file with automatic header detection and encoding detection.

        Args:
            file_path: Path to CSV file

        Returns:
            Tuple of (DataFrame, header_info dict)
        """
        supported_encodings = self.source_config.get('supported_encodings', ['utf-8', 'latin-1', 'cp1252'])
        warnings = []

        # Try encodings
        df = None
        encoding_used = None

        for encoding in supported_encodings:
            try:
                df_preview = pd.read_csv(file_path, encoding=encoding, header=None, nrows=20)
                encoding_used = encoding
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            raise ValueError(f"Could not read CSV with any supported encoding: {supported_encodings}")

        # Detect header row
        header_row = self._detect_header_row(df_preview)

        if header_row is None:
            warnings.append("Could not detect header row, using first row")
            header_row = 0

        if header_row > 0:
            warnings.append(f"Header detected at row {header_row}, skipping {header_row} metadata rows")

        # Read full file with detected header
        df = pd.read_csv(file_path, encoding=encoding_used, skiprows=header_row)

        # Drop rows that are all NaN
        df = df.dropna(how='all').reset_index(drop=True)

        header_info = {
            'encoding': encoding_used,
            'header_row': header_row,
            'metadata_rows_skipped': header_row,
            'warnings': warnings
        }

        return df, header_info

    def _ingest_google_sheets(self, sheet_url: str) -> Tuple[pd.DataFrame, IngestionMetadata]:
        """
        Ingest from Google Sheets using Google Sheets API.

        Args:
            sheet_url: Google Sheets URL

        Returns:
            Tuple of (DataFrame, IngestionMetadata)

        Note:
            Uses Google Sheets API with OAuth credentials from generate_markdown_summary.py
            Falls back to public export if API access fails.
        """
        warnings = []

        # Extract sheet ID from URL
        # Format: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit...
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_url)
        if not match:
            raise ValueError(f"Could not extract sheet ID from URL: {sheet_url}")

        sheet_id = match.group(1)

        # Extract gid (sheet tab ID) if present - we'll need to convert to sheet name
        gid_match = re.search(r'[#&]gid=(\d+)', sheet_url)
        gid = gid_match.group(1) if gid_match else '0'

        # Try API access first
        try:
            df = self._read_sheets_via_api(sheet_id, gid, warnings)
        except Exception as api_error:
            warnings.append(f"API access failed: {str(api_error)}, trying public export")
            # Fall back to public export URL
            try:
                df = self._read_sheets_via_export(sheet_id, gid, warnings)
            except Exception as export_error:
                raise ValueError(
                    f"Failed to read Google Sheets via both API and public export.\n"
                    f"API error: {str(api_error)}\n"
                    f"Export error: {str(export_error)}\n"
                    f"Make sure the sheet is shared with the service account or publicly accessible."
                )

        # Check for standard Google Sheets format first (header on row 61)
        gs_config = self.source_config.get('google_sheets', {})
        header_row_detected = None

        if gs_config.get('detect_standard_format', False):
            std_format = gs_config.get('standard_format', {})
            expected_header_row = std_format.get('header_row', 61) - 1  # Convert to 0-indexed
            expected_headers = std_format.get('expected_headers', [])
            min_match = std_format.get('min_headers_match', 4)

            # Check if we have enough rows to check the standard format
            if len(df) > expected_header_row and expected_headers:
                # Get the row that should be the header
                candidate_header = df.iloc[expected_header_row]

                # Check how many expected headers match
                matches = 0
                for i, expected in enumerate(expected_headers):
                    if i < len(candidate_header) and candidate_header.iloc[i] == expected:
                        matches += 1

                # If enough headers match, use this as the header row
                if matches >= min_match:
                    header_row_detected = expected_header_row
                    warnings.append(
                        f"Detected standard Google Sheets format: headers on row {expected_header_row + 1} "
                        f"({matches}/{len(expected_headers)} expected headers matched)"
                    )

        # If standard format not detected, use automatic header detection
        if header_row_detected is None:
            header_row_detected = self._detect_header_row(df.head(20))

        # Apply header row detection
        if header_row_detected is not None and header_row_detected > 0:
            if header_row_detected not in [row - 1 for row in [gs_config.get('standard_format', {}).get('header_row', 0)]]:
                warnings.append(f"Header detected at row {header_row_detected + 1}, skipping {header_row_detected} metadata rows")

            df = df.iloc[header_row_detected:].reset_index(drop=True)
            # Use first row as header
            df.columns = df.iloc[0]
            df = df.iloc[1:].reset_index(drop=True)

        # Drop all-NaN rows
        df = df.dropna(how='all').reset_index(drop=True)

        metadata = IngestionMetadata(
            rows_read=len(df),
            columns_read=len(df.columns),
            encoding='utf-8',
            header_row=header_row_detected + 1 if header_row_detected is not None else None,
            metadata_rows_skipped=header_row_detected if header_row_detected is not None else None,
            warnings=warnings
        )

        return df, metadata

    def _read_sheets_via_api(self, sheet_id: str, gid: str, warnings: List[str]) -> pd.DataFrame:
        """
        Read Google Sheets using the Google Sheets API.

        Args:
            sheet_id: Google Sheets ID
            gid: Sheet tab gid (0 for first sheet)
            warnings: List to append warnings to

        Returns:
            DataFrame with sheet data
        """
        from googleapiclient.discovery import build
        import google.auth

        # Try Application Default Credentials (ADC) first
        try:
            creds, project = google.auth.default(
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets.readonly',
                    'https://www.googleapis.com/auth/drive.readonly'
                ]
            )
        except Exception as e:
            raise FileNotFoundError(
                f"Google Cloud credentials not found: {str(e)}\n"
                "Please authenticate with Google Cloud:\n"
                "  gcloud auth application-default login\n"
                "\nOr run the setup script to verify:\n"
                "  cd /Users/eugenetsenter/gh_projects/multi_agent_ai_project/agents/data_harmonization\n"
                "  python setup_sheets_auth.py"
            )

        # Build Sheets API service
        try:
            service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
        except Exception as e:
            raise ValueError(f"Failed to build Google Sheets service: {str(e)}")

        # Get spreadsheet metadata to find sheet name from gid
        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = spreadsheet.get('sheets', [])

        # Find the sheet by gid
        sheet_name = None
        for sheet in sheets:
            if str(sheet['properties'].get('sheetId', '0')) == gid:
                sheet_name = sheet['properties']['title']
                break

        # If no gid match, use first sheet
        if not sheet_name and sheets:
            sheet_name = sheets[0]['properties']['title']
            warnings.append(f"Could not find sheet with gid={gid}, using first sheet: {sheet_name}")

        # Read the data
        range_name = sheet_name if sheet_name else 'Sheet1'
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()

        values = result.get('values', [])
        if not values:
            raise ValueError("No data found in Google Sheet")

        # Convert to DataFrame
        df = pd.DataFrame(values)

        return df

    def _read_sheets_via_export(self, sheet_id: str, gid: str, warnings: List[str]) -> pd.DataFrame:
        """
        Read Google Sheets via public export URL (fallback method).

        Args:
            sheet_id: Google Sheets ID
            gid: Sheet tab gid
            warnings: List to append warnings to

        Returns:
            DataFrame with sheet data
        """
        # Build export URL (CSV format)
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

        # Read directly from export URL
        df = pd.read_csv(export_url)
        warnings.append("Used public export URL (sheet must be publicly accessible)")

        return df

    def _ingest_s3(self, s3_path: str) -> Tuple[pd.DataFrame, IngestionMetadata]:
        """Ingest from S3 (placeholder for future implementation)."""
        raise NotImplementedError("S3 ingestion not yet implemented")

    def _ingest_sftp(self, sftp_path: str) -> Tuple[pd.DataFrame, IngestionMetadata]:
        """Ingest from SFTP (placeholder for future implementation)."""
        raise NotImplementedError("SFTP ingestion not yet implemented")

    def _ingest_bigquery(self, query_or_table: str) -> Tuple[pd.DataFrame, IngestionMetadata]:
        """Ingest from BigQuery (placeholder for future implementation)."""
        raise NotImplementedError("BigQuery ingestion not yet implemented")
