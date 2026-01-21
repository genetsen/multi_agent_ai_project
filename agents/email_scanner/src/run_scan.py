#!/usr/bin/env python3
"""
Email Scanner CLI - Run data email scans

Scans Gmail inbox for first-party data deliveries and routes them
to the Data Harmonization pipeline or review queue.

Usage:
    python -m agents.email_scanner.src.run_scan --days 7
    python -m agents.email_scanner.src.run_scan --after 2026/01/15 --before 2026/01/21
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from .gmail_client import create_gmail_client
from .scanner import EmailScanner, PartnerPattern

load_dotenv()

# System senders to exclude (matches generate_markdown_summary.py)
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

# Default output directory
DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "scan_results"
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Scan Gmail for first-party data deliveries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Scan last 7 days
    python run_scan.py --days 7

    # Scan specific date range
    python run_scan.py --after 2026/01/15 --before 2026/01/21

    # Scan with custom patterns file
    python run_scan.py --days 7 --patterns patterns.json

    # Output results to specific directory
    python run_scan.py --days 7 --output ./results
        """,
    )

    # Date range options
    parser.add_argument(
        "-d", "--days",
        type=int,
        default=1,
        help="Number of days to scan back (default: 1)",
    )
    parser.add_argument(
        "-a", "--after",
        help="Start date YYYY/MM/DD inclusive",
    )
    parser.add_argument(
        "-b", "--before",
        help="End date YYYY/MM/DD exclusive",
    )

    # Filter options
    parser.add_argument(
        "-c", "--category",
        default="primary",
        help="Gmail category to scan: primary, social, promotions, updates, forums (default: primary)",
    )
    parser.add_argument(
        "--max-emails",
        type=int,
        default=100,
        help="Maximum emails to process (default: 100)",
    )

    # Configuration
    parser.add_argument(
        "-p", "--patterns",
        help="Path to partner patterns JSON file",
    )
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for scan results (default: {DEFAULT_OUTPUT_DIR})",
    )

    # Behavior
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify emails but don't extract attachments",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Calculate date range
    if args.after:
        args.since = datetime.strptime(args.after, "%Y/%m/%d")
    else:
        args.since = datetime.now() - timedelta(days=args.days)

    if args.before:
        args.until = datetime.strptime(args.before, "%Y/%m/%d")
    else:
        args.until = datetime.now()

    return args


def load_patterns(patterns_path: str) -> list[PartnerPattern]:
    """Load partner patterns from JSON file."""
    if not patterns_path or not os.path.exists(patterns_path):
        return []

    with open(patterns_path, 'r') as f:
        data = json.load(f)

    patterns = []
    for p in data.get('patterns', []):
        patterns.append(PartnerPattern(
            partner_name=p['partner_name'],
            sender_patterns=p.get('sender_patterns', []),
            subject_patterns=p.get('subject_patterns', []),
            expected_format=p.get('expected_format'),
            expected_columns=p.get('expected_columns'),
            column_aliases=p.get('column_aliases', {}),
            auto_process=p.get('auto_process', True),
            confidence_threshold=p.get('confidence_threshold', 0.8),
        ))

    return patterns


def is_system_sender(from_header: str) -> bool:
    """Check if sender is an automated/system sender."""
    header_lower = (from_header or "").lower()
    for token in SYSTEM_SENDER_TOKENS:
        if token in header_lower:
            return True
    return False


def main():
    """Main entry point."""
    args = parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    logger = logging.getLogger(__name__)

    # Load patterns
    patterns = load_patterns(args.patterns) if args.patterns else []
    logger.info(f"Loaded {len(patterns)} partner patterns")

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize Gmail client
    logger.info("Authenticating with Gmail...")
    gmail_client = create_gmail_client()

    # Initialize scanner
    scanner = EmailScanner(
        gmail_client=gmail_client,
        patterns=patterns,
        extraction_dir=str(output_dir / "extracts"),
        blocklist_senders=SYSTEM_SENDER_TOKENS,
    )

    # Run scan
    logger.info(f"Scanning emails from {args.since} to {args.until}...")
    logger.info(f"Category: {args.category}, Max emails: {args.max_emails}")

    results = scanner.scan(
        since=args.since,
        max_results=args.max_emails,
    )

    # Filter out system senders from results
    # (Additional filtering in case any slipped through)
    filtered_auto = [
        p for p in results.get('auto_processed', [])
        if not is_system_sender(p.get('raw_sources', [{}])[0].get('email_metadata', {}).get('from', ''))
    ]
    filtered_review = [
        r for r in results.get('review_queue', [])
        if not is_system_sender(r.get('email_summary', {}).get('from', ''))
    ]

    results['auto_processed'] = filtered_auto
    results['review_queue'] = filtered_review

    # Save results
    run_id = results.get('run_id', f"es-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    results_file = output_dir / f"{run_id}.json"

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)
    print(f"Run ID: {run_id}")
    print(f"Emails scanned: {results.get('emails_scanned', 0)}")
    print(f"Classified as data: {results.get('emails_classified_as_data', 0)}")
    print(f"Auto-processed: {len(results.get('auto_processed', []))}")
    print(f"Queued for review: {len(results.get('review_queue', []))}")
    print(f"Errors: {len(results.get('errors', []))}")
    print(f"\nResults saved to: {results_file}")

    # Print auto-processed summary
    if results.get('auto_processed'):
        print("\n--- AUTO-PROCESSED ---")
        for payload in results['auto_processed']:
            partner = payload.get('partner_name', 'Unknown')
            confidence = payload.get('pattern_match_confidence', 0)
            sources = payload.get('raw_sources', [])
            print(f"  • {partner} (confidence: {confidence:.2f})")
            for src in sources:
                meta = src.get('email_metadata', {})
                print(f"    Subject: {meta.get('subject', 'N/A')[:50]}")

    # Print review queue summary
    if results.get('review_queue'):
        print("\n--- REVIEW QUEUE ---")
        for item in results['review_queue']:
            email_summary = item.get('email_summary', {})
            score = item.get('classification_score', 0)
            print(f"  • Score: {score:.2f}")
            print(f"    From: {email_summary.get('from', 'N/A')[:40]}")
            print(f"    Subject: {email_summary.get('subject', 'N/A')[:50]}")

    # Print errors
    if results.get('errors'):
        print("\n--- ERRORS ---")
        for error in results['errors']:
            print(f"  • {error.get('email_id', 'Unknown')}: {error.get('error', 'Unknown error')}")

    print("\n" + "=" * 60)

    return 0 if not results.get('errors') else 1


if __name__ == "__main__":
    sys.exit(main())
