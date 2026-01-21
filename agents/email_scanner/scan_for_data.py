#!/usr/bin/env python3
"""
Email Data Scanner - Find first-party data deliveries in Gmail

Scans Gmail inbox for emails containing data files (CSV, Excel, etc.)
from partners. Outputs a JSON file with email metadata and attachment info
ready for the Data Harmonization pipeline.

Usage:
    python scan_for_data.py --days 7
    python scan_for_data.py --partner "PartnerA"
    python scan_for_data.py --days 7 --partner "PartnerA"
    python scan_for_data.py --after 2026/01/15 --before 2026/01/21
"""
import argparse
import base64
import json
import os
import pickle
import re
from datetime import datetime, timedelta
from email.utils import parseaddr
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# System senders to exclude
SYSTEM_SENDER_TOKENS = [
    "noreply",
    "no-reply",
    "notification@",
    "alert@",
    "mailer-daemon",
    "postmaster",
    "datorama.com",
    "sisense.com",
    "apps-scripts-notifications@google.com",
    "do-not-reply",
    "donotreply",
    "auto-reply",
    "automated",
    "bounce",
]

# Data file extensions we care about
DATA_EXTENSIONS = [".csv", ".xlsx", ".xls", ".tsv", ".json", ".xml"]

# Keywords that suggest data delivery emails
DATA_SUBJECT_KEYWORDS = [
    "report",
    "data",
    "export",
    "metrics",
    "analytics",
    "performance",
    "weekly",
    "daily",
    "monthly",
]

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan_results")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Scan Gmail for first-party data deliveries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scan_for_data.py --days 7
    python scan_for_data.py --partner "PartnerA"
    python scan_for_data.py --days 7 --partner "PartnerA" --has-attachment
    python scan_for_data.py --after 2026/01/15 --before 2026/01/21
        """,
    )

    # Date options
    parser.add_argument(
        "-d", "--days",
        type=int,
        default=7,
        help="Number of days to look back (default: 7)",
    )
    parser.add_argument(
        "-a", "--after",
        help="Start date YYYY/MM/DD inclusive (overrides --days)",
    )
    parser.add_argument(
        "-b", "--before",
        help="End date YYYY/MM/DD exclusive",
    )

    # Filter options
    parser.add_argument(
        "-p", "--partner",
        help="Filter by partner name (searches sender address and subject)",
    )
    parser.add_argument(
        "--has-attachment",
        action="store_true",
        help="Only include emails with data file attachments",
    )
    parser.add_argument(
        "--data-keywords",
        action="store_true",
        help="Only include emails with data-related keywords in subject",
    )

    # Output options
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file path (default: scan_results/scan_TIMESTAMP.json)",
    )
    parser.add_argument(
        "--save-attachments",
        action="store_true",
        help="Download and save data file attachments",
    )

    args = parser.parse_args()

    # Calculate dates
    if args.after:
        args.after_date = args.after
    else:
        after_dt = datetime.now() - timedelta(days=args.days)
        args.after_date = after_dt.strftime("%Y/%m/%d")

    if args.before:
        args.before_date = args.before
    else:
        args.before_date = (datetime.now() + timedelta(days=1)).strftime("%Y/%m/%d")

    # Default output path
    if not args.output:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = os.path.join(OUTPUT_DIR, f"scan_{timestamp}.json")

    return args


def build_gmail_service():
    """Build Gmail service using interactive OAuth flow or cached token."""
    TOKEN_FILE = os.path.expanduser("~/.cache/gmail_token.pickle")

    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials_paths = [
                "credentials.json",
                os.path.expanduser("~/credentials.json"),
                os.path.expanduser("~/.secrets/credentials.json"),
            ]
            credentials_path = None
            for path in credentials_paths:
                if os.path.exists(path):
                    credentials_path = path
                    break

            if not credentials_path:
                raise FileNotFoundError(
                    "\nNo credentials.json found. To set up:\n"
                    "1. Go to https://console.cloud.google.com/\n"
                    "2. Create a new project (or select existing)\n"
                    "3. Enable Gmail API\n"
                    "4. Create OAuth 2.0 credentials (Desktop app)\n"
                    "5. Download the credentials as JSON\n"
                    "6. Save to project root as 'credentials.json'\n"
                )

            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            print("Opening browser for Gmail authorization...")
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def is_system_sender(from_header):
    """Check if sender is an automated/system sender."""
    header_lower = (from_header or "").lower()
    _, addr = parseaddr(from_header or "")
    addr = addr.lower()
    for token in SYSTEM_SENDER_TOKENS:
        if token in header_lower or token in addr:
            return True
    return False


def is_data_file(filename):
    """Check if filename is a data file we care about."""
    if not filename:
        return False
    ext = os.path.splitext(filename.lower())[1]
    return ext in DATA_EXTENSIONS


def has_data_keywords(subject):
    """Check if subject contains data-related keywords."""
    subject_lower = (subject or "").lower()
    return any(kw in subject_lower for kw in DATA_SUBJECT_KEYWORDS)


def matches_partner(record, partner_filter):
    """Check if email matches partner filter."""
    if not partner_filter:
        return True
    partner_lower = partner_filter.lower()
    from_lower = record.get("from", "").lower()
    subject_lower = record.get("subject", "").lower()
    return partner_lower in from_lower or partner_lower in subject_lower


def collect_attachments(payload):
    """Collect attachment info from email payload."""
    attachments = []

    def walk(part):
        filename = part.get("filename")
        body = part.get("body", {})
        if filename:
            attachments.append({
                "filename": filename,
                "mime_type": part.get("mimeType", ""),
                "size": body.get("size", 0),
                "attachment_id": body.get("attachmentId", ""),
                "is_data_file": is_data_file(filename),
            })
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload or {})
    return attachments


def decode_base64url(data):
    """Decode base64url encoded data."""
    if not data:
        return ""
    padding = "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(data + padding).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def extract_text(payload):
    """Extract text content from email payload."""
    plain_parts = []

    def walk(part):
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if mime == "text/plain" and data:
            plain_parts.append(decode_base64url(data))
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload or {})
    return "\n".join(plain_parts) if plain_parts else ""


def extract_links(text):
    """Extract potential data links from email body."""
    links = []
    patterns = {
        "google_sheets": r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)",
        "dropbox": r"(dropbox\.com/s/[a-zA-Z0-9]+)",
        "box": r"(box\.com/s/[a-zA-Z0-9]+)",
        "onedrive": r"(1drv\.ms/[a-zA-Z0-9]+)",
    }
    for link_type, pattern in patterns.items():
        matches = re.findall(pattern, text, re.I)
        for match in matches:
            links.append({"type": link_type, "match": match})
    return links


def message_to_record(msg):
    """Convert Gmail API message to a data record."""
    payload = msg.get("payload", {}) or {}
    headers = {}
    for header in payload.get("headers", []) or []:
        name = header.get("name")
        value = header.get("value")
        if name and value:
            headers[name.lower()] = value

    body_text = extract_text(payload)
    attachments = collect_attachments(payload)
    data_attachments = [a for a in attachments if a.get("is_data_file")]
    data_links = extract_links(body_text)

    return {
        "id": msg.get("id", ""),
        "thread_id": msg.get("threadId", msg.get("id", "")),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": msg.get("snippet", "") or "",
        "permalink": f"https://mail.google.com/mail/u/0/#inbox/{msg.get('id', '')}",
        "attachments": attachments,
        "data_attachments": data_attachments,
        "data_links": data_links,
        "has_data": len(data_attachments) > 0 or len(data_links) > 0,
    }


def download_attachment(service, message_id, attachment_id, filename, output_dir):
    """Download an attachment and save to disk."""
    result = service.users().messages().attachments().get(
        userId="me",
        messageId=message_id,
        id=attachment_id,
    ).execute()

    data = result.get("data", "")
    padding = "=" * (-len(data) % 4)
    file_data = base64.urlsafe_b64decode(data + padding)

    # Safe filename
    safe_name = re.sub(r'[^\w\-_\.]', '_', filename)
    file_path = os.path.join(output_dir, safe_name)

    # Handle duplicates
    counter = 1
    base, ext = os.path.splitext(file_path)
    while os.path.exists(file_path):
        file_path = f"{base}_{counter}{ext}"
        counter += 1

    with open(file_path, "wb") as f:
        f.write(file_data)

    return file_path


def main():
    """Main entry point."""
    args = parse_args()

    print(f"Scanning emails from {args.after_date} to {args.before_date}...")
    if args.partner:
        print(f"Filtering by partner: {args.partner}")

    # Build Gmail service
    service = build_gmail_service()

    # Build query
    query_parts = [
        "in:inbox",
        "category:primary",
        f"after:{args.after_date}",
        f"before:{args.before_date}",
    ]
    if args.partner:
        query_parts.append(f"({args.partner})")
    if args.has_attachment:
        query_parts.append("has:attachment")

    query = " ".join(query_parts)
    print(f"Query: {query}")

    # Fetch message IDs
    ids = []
    req = service.users().messages().list(userId="me", q=query, includeSpamTrash=False)
    while req is not None:
        resp = req.execute()
        for msg in resp.get("messages", []):
            ids.append(msg)
        req = service.users().messages().list_next(req, resp)

    print(f"Found {len(ids)} emails matching query")

    # Fetch full messages and filter
    records = []
    for ref in ids:
        msg_id = ref.get("id")
        if not msg_id:
            continue

        msg = service.users().messages().get(
            userId="me", id=msg_id, format="full"
        ).execute()

        record = message_to_record(msg)

        # Skip system senders
        if is_system_sender(record.get("from", "")):
            continue

        # Apply filters
        if args.partner and not matches_partner(record, args.partner):
            continue

        if args.data_keywords and not has_data_keywords(record.get("subject", "")):
            continue

        if args.has_attachment and not record.get("data_attachments"):
            continue

        records.append(record)

    print(f"After filtering: {len(records)} emails")

    # Count data emails
    data_emails = [r for r in records if r.get("has_data")]
    print(f"Emails with data (attachments or links): {len(data_emails)}")

    # Download attachments if requested
    if args.save_attachments and data_emails:
        attach_dir = os.path.join(os.path.dirname(args.output), "attachments")
        os.makedirs(attach_dir, exist_ok=True)
        print(f"\nDownloading attachments to: {attach_dir}")

        for record in data_emails:
            for att in record.get("data_attachments", []):
                if att.get("attachment_id"):
                    try:
                        path = download_attachment(
                            service,
                            record["id"],
                            att["attachment_id"],
                            att["filename"],
                            attach_dir,
                        )
                        att["local_path"] = path
                        print(f"  Saved: {att['filename']}")
                    except Exception as e:
                        print(f"  Error downloading {att['filename']}: {e}")

    # Build output
    output = {
        "scan_metadata": {
            "scan_time": datetime.now().isoformat(),
            "after": args.after_date,
            "before": args.before_date,
            "partner_filter": args.partner,
            "total_emails_scanned": len(ids),
            "emails_after_filtering": len(records),
            "emails_with_data": len(data_emails),
        },
        "data_emails": data_emails,
        "all_emails": records,
    }

    # Write output
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {args.output}")

    # Print summary
    if data_emails:
        print("\n" + "=" * 60)
        print("DATA EMAILS FOUND")
        print("=" * 60)
        for record in data_emails:
            print(f"\nFrom: {record['from'][:50]}")
            print(f"Subject: {record['subject'][:60]}")
            print(f"Date: {record['date']}")
            if record.get("data_attachments"):
                print("Attachments:")
                for att in record["data_attachments"]:
                    print(f"  - {att['filename']} ({att.get('size', 0)} bytes)")
            if record.get("data_links"):
                print("Links:")
                for link in record["data_links"]:
                    print(f"  - {link['type']}: {link['match']}")
            print(f"Link: {record['permalink']}")
        print("=" * 60)
    else:
        print("\nNo emails with data files found.")


if __name__ == "__main__":
    main()
