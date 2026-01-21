"""
Email Scanner Agent - Source modules

This package provides the core functionality for the Email Scanner Agent:
- Gmail API integration
- Email classification
- Attachment extraction
- Pattern matching and routing
"""

from .gmail_client import (
    GmailClient,
    EmailMessage,
    EmailAttachment,
    create_gmail_client,
    build_gmail_service,
)

from .scanner import (
    EmailScanner,
    EmailClassifier,
    PatternMatcher,
    Classification,
    ClassificationResult,
    ExtractedAsset,
    PartnerPattern,
    ScanResult,
)

__all__ = [
    # Gmail client
    "GmailClient",
    "EmailMessage",
    "EmailAttachment",
    "create_gmail_client",
    "build_gmail_service",
    # Scanner
    "EmailScanner",
    "EmailClassifier",
    "PatternMatcher",
    "Classification",
    "ClassificationResult",
    "ExtractedAsset",
    "PartnerPattern",
    "ScanResult",
]
