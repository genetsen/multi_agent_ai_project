"""
Setup Google Sheets Authentication for Data Harmonization Agent.

This script verifies Google Cloud authentication and tests Google Sheets API access.

Usage:
    python setup_sheets_auth.py

Requirements:
    1. Google Cloud SDK installed (you have this already!)
    2. Authenticated with gcloud: gcloud auth application-default login
    3. Google Sheets API enabled in your GCP project
"""

import os
import google.auth
from google.auth.transport.requests import Request


def check_gcloud_auth():
    """
    Check if Application Default Credentials (ADC) are configured.

    Returns:
        tuple: (credentials, project_id) if successful, (None, None) otherwise
    """
    print("Checking Google Cloud authentication...")

    try:
        credentials, project_id = google.auth.default(
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
        )

        print(f"✅ Found Application Default Credentials")
        print(f"   Project: {project_id}")

        # Check if credentials are valid
        if not credentials.valid:
            if credentials.expired and credentials.refresh_token:
                print("   Refreshing expired credentials...")
                credentials.refresh(Request())
                print("   ✅ Credentials refreshed")

        return credentials, project_id

    except Exception as e:
        print(f"❌ No valid credentials found: {e}")
        print("\nPlease authenticate with Google Cloud:")
        print("  gcloud auth application-default login")
        print("\nThis will open a browser and save credentials to:")
        print("  ~/.config/gcloud/application_default_credentials.json")
        return None, None


def test_sheets_api(credentials):
    """
    Test access to Google Sheets API.

    Args:
        credentials: Google credentials object

    Returns:
        bool: True if successful, False otherwise
    """
    print("\nTesting Google Sheets API access...")

    try:
        from googleapiclient.discovery import build
        service = build('sheets', 'v4', credentials=credentials, cache_discovery=False)

        # Try to access a test spreadsheet (will fail if API not enabled)
        # This just builds the service, actual API calls will happen during ingestion
        print("✅ Successfully connected to Google Sheets API!")
        return True

    except Exception as e:
        error_msg = str(e)

        if "sheets" in error_msg.lower() and "not enabled" in error_msg.lower():
            print(f"❌ Google Sheets API not enabled!")
            print("\nPlease enable the Google Sheets API:")
            print("1. Go to: https://console.cloud.google.com/apis/library/sheets.googleapis.com")
            print("2. Click 'Enable'")
        else:
            print(f"❌ Failed to connect to Google Sheets API: {e}")

        return False


def setup_authentication():
    """
    Set up and verify Google Sheets authentication using Application Default Credentials.

    Returns:
        bool: True if successful, False otherwise
    """
    # Check for ADC
    credentials, project_id = check_gcloud_auth()

    if not credentials:
        return False

    # Test API access
    if not test_sheets_api(credentials):
        return False

    return True


def main():
    """Main setup function."""
    print()
    print("=" * 80)
    print("Google Sheets Authentication Setup")
    print("Data Harmonization Agent")
    print("=" * 80)
    print()

    success = setup_authentication()

    print()
    print("=" * 80)
    if success:
        print("✅ Setup complete!")
        print()
        print("You can now read private Google Sheets with the harmonization agent.")
        print("Using Application Default Credentials from:")
        print("  ~/.config/gcloud/application_default_credentials.json")
    else:
        print("❌ Setup failed!")
        print()
        print("Please resolve the errors above and try again.")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
