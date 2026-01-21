"""
Gmail API Client for Email Scanner Agent

Handles OAuth2 authentication, email retrieval, and message parsing
for the Email Scanner Agent pipeline.

Uses the same authentication pattern as generate_markdown_summary.py
"""

import os
import base64
import pickle
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Generator
from dataclasses import dataclass, field
from pathlib import Path
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Gmail API scopes - readonly for scanning, modify for labeling
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Default token location (matches generate_markdown_summary.py)
DEFAULT_TOKEN_FILE = os.path.expanduser("~/.cache/gmail_token.pickle")

# Credentials file search paths
CREDENTIALS_PATHS = [
    "credentials.json",
    os.path.expanduser("~/credentials.json"),
    os.path.expanduser("~/.secrets/credentials.json"),
]


@dataclass
class EmailAttachment:
    """Represents an email attachment."""
    filename: str
    mime_type: str
    size: int
    attachment_id: str
    data: Optional[bytes] = None  # Populated when downloaded


@dataclass
class EmailMessage:
    """Represents a parsed email message."""
    message_id: str
    thread_id: str
    from_address: str
    to_addresses: List[str]
    subject: str
    date: datetime
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    attachments: List[EmailAttachment] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    snippet: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    permalink: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "thread_id": self.thread_id,
            "from": self.from_address,
            "to": self.to_addresses,
            "subject": self.subject,
            "date": self.date.isoformat(),
            "body_text": self.body_text,
            "body_html": self.body_html,
            "attachments": [
                {
                    "filename": a.filename,
                    "mime_type": a.mime_type,
                    "size": a.size,
                }
                for a in self.attachments
            ],
            "labels": self.labels,
            "snippet": self.snippet,
            "permalink": self.permalink,
        }


def build_gmail_service(token_file: str = DEFAULT_TOKEN_FILE) -> Any:
    """
    Build Gmail service using interactive OAuth flow or cached token.

    This function matches the authentication pattern used in
    generate_markdown_summary.py for compatibility.

    Args:
        token_file: Path to cached token pickle file

    Returns:
        Gmail API service object
    """
    creds = None

    # Load existing token if available
    if os.path.exists(token_file):
        with open(token_file, "rb") as token:
            creds = pickle.load(token)

    # If no valid credentials, get new ones through OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            # Try to find credentials.json in common locations
            credentials_path = None
            for path in CREDENTIALS_PATHS:
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
                    "Then run this script again."
                )

            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            print("Opening browser for Gmail authorization...")
            creds = flow.run_local_server(port=0)

        # Save token for future runs
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, "wb") as token:
            pickle.dump(creds, token)

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


class GmailClient:
    """
    Gmail API client for the Email Scanner Agent.

    Handles authentication, email retrieval, and attachment extraction.

    Usage:
        client = GmailClient()

        for email in client.fetch_emails(since=datetime.now() - timedelta(days=1)):
            print(email.subject)
    """

    def __init__(
        self,
        token_file: str = DEFAULT_TOKEN_FILE,
        user_id: str = "me",
    ):
        """
        Initialize the Gmail client.

        Args:
            token_file: Path to cached token pickle file
            user_id: Gmail user ID (default "me" for authenticated user)
        """
        self.token_file = token_file
        self.user_id = user_id
        self.service = None

    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth2.

        Returns:
            True if authentication successful
        """
        self.service = build_gmail_service(self.token_file)
        logger.info("Gmail API service initialized successfully")
        return True

    def _ensure_authenticated(self):
        """Ensure client is authenticated before API calls."""
        if not self.service:
            self.authenticate()

    def build_query(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        from_addresses: Optional[List[str]] = None,
        subject_contains: Optional[List[str]] = None,
        has_attachment: bool = False,
        in_inbox: bool = True,
        category: Optional[str] = None,  # "primary", "social", "promotions", etc.
        is_unread: Optional[bool] = None,
    ) -> str:
        """
        Build Gmail search query string.

        Args:
            since: Only emails after this datetime (format: YYYY/MM/DD)
            until: Only emails before this datetime
            from_addresses: Filter by sender addresses/domains
            subject_contains: Subject must contain one of these
            has_attachment: Only emails with attachments
            in_inbox: Filter to inbox only
            category: Gmail category (primary, social, promotions, etc.)
            is_unread: Filter by read/unread status

        Returns:
            Gmail query string
        """
        query_parts = []

        if since:
            # Gmail uses YYYY/MM/DD format for after: query
            query_parts.append(f"after:{since.strftime('%Y/%m/%d')}")

        if until:
            query_parts.append(f"before:{until.strftime('%Y/%m/%d')}")

        if from_addresses:
            # OR together multiple from addresses
            from_query = " OR ".join(f"from:{addr}" for addr in from_addresses)
            if len(from_addresses) > 1:
                from_query = f"({from_query})"
            query_parts.append(from_query)

        if subject_contains:
            # OR together subject terms
            subj_query = " OR ".join(f'subject:"{term}"' for term in subject_contains)
            if len(subject_contains) > 1:
                subj_query = f"({subj_query})"
            query_parts.append(subj_query)

        if has_attachment:
            query_parts.append("has:attachment")

        if in_inbox:
            query_parts.append("in:inbox")

        if category:
            query_parts.append(f"category:{category}")

        if is_unread is True:
            query_parts.append("is:unread")
        elif is_unread is False:
            query_parts.append("is:read")

        return " ".join(query_parts)

    def list_message_ids(self, query: str) -> List[Dict[str, str]]:
        """
        List message IDs matching query (handles pagination).

        Args:
            query: Gmail search query

        Returns:
            List of message references with 'id' and 'threadId'
        """
        self._ensure_authenticated()

        ids = []
        req = self.service.users().messages().list(
            userId=self.user_id,
            q=query,
            includeSpamTrash=False,
        )

        while req is not None:
            resp = req.execute()
            for msg in resp.get("messages", []):
                ids.append(msg)
            req = self.service.users().messages().list_next(req, resp)

        return ids

    def fetch_emails(
        self,
        query: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        max_results: int = 100,
        include_body: bool = True,
        include_attachments: bool = True,
        in_inbox: bool = True,
        category: Optional[str] = None,
    ) -> Generator[EmailMessage, None, None]:
        """
        Fetch emails matching criteria.

        Args:
            query: Gmail search query (or use since/until for simple queries)
            since: Only emails after this datetime
            until: Only emails before this datetime
            max_results: Maximum emails to return
            include_body: Whether to fetch full body content
            include_attachments: Whether to fetch attachment metadata
            in_inbox: Filter to inbox only
            category: Gmail category filter

        Yields:
            EmailMessage objects
        """
        self._ensure_authenticated()

        # Build query if not provided
        if not query:
            query = self.build_query(
                since=since,
                until=until,
                in_inbox=in_inbox,
                category=category,
            )

        logger.info(f"Fetching emails with query: {query or '(none)'}")

        msg_refs = self.list_message_ids(query)
        logger.info(f"Found {len(msg_refs)} messages")

        # Limit results
        msg_refs = msg_refs[:max_results]

        # Fetch full details for each message
        for msg_ref in msg_refs:
            try:
                email = self._fetch_message_details(
                    msg_ref['id'],
                    include_body=include_body,
                    include_attachments=include_attachments,
                )
                if email:
                    yield email
            except HttpError as e:
                logger.error(f"Error fetching message {msg_ref['id']}: {e}")
                continue

    def _fetch_message_details(
        self,
        message_id: str,
        include_body: bool = True,
        include_attachments: bool = True,
    ) -> Optional[EmailMessage]:
        """
        Fetch full details for a single message.

        Args:
            message_id: Gmail message ID
            include_body: Whether to parse body content
            include_attachments: Whether to get attachment metadata

        Returns:
            Parsed EmailMessage or None on error
        """
        msg = self.service.users().messages().get(
            userId=self.user_id,
            id=message_id,
            format='full',
        ).execute()

        return self._parse_message(msg, include_body, include_attachments)

    def _parse_message(
        self,
        msg: Dict[str, Any],
        include_body: bool,
        include_attachments: bool,
    ) -> EmailMessage:
        """
        Parse Gmail API message response into EmailMessage.

        Args:
            msg: Raw Gmail API message dict
            include_body: Whether to extract body
            include_attachments: Whether to extract attachment info

        Returns:
            Parsed EmailMessage
        """
        payload = msg.get('payload', {})
        headers = {}

        # Extract headers
        for header in payload.get('headers', []):
            name = header.get('name', '').lower()
            value = header.get('value', '')
            if name and value:
                headers[name] = value

        # Parse date
        date_str = headers.get('date', '')
        try:
            date = parsedate_to_datetime(date_str)
        except (ValueError, TypeError):
            date = datetime.now()

        # Parse addresses
        from_addr = headers.get('from', '')
        to_addrs = [a.strip() for a in headers.get('to', '').split(',') if a.strip()]

        # Extract body
        body_text = None
        body_html = None
        if include_body:
            body_text, body_html = self._extract_body(payload)

        # Extract attachments
        attachments = []
        if include_attachments:
            attachments = self._extract_attachment_metadata(msg['id'], payload)

        # Build permalink
        permalink = f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}"

        return EmailMessage(
            message_id=msg['id'],
            thread_id=msg.get('threadId', ''),
            from_address=from_addr,
            to_addresses=to_addrs,
            subject=headers.get('subject', '(no subject)'),
            date=date,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            labels=msg.get('labelIds', []),
            snippet=msg.get('snippet', ''),
            headers=headers,
            permalink=permalink,
        )

    def _decode_base64url(self, data: str) -> str:
        """Decode base64url encoded data."""
        if not data:
            return ""
        padding = "=" * (-len(data) % 4)
        try:
            return base64.urlsafe_b64decode(data + padding).decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _extract_body(self, payload: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        """
        Extract text and HTML body from message payload.

        Handles both simple and multipart messages.

        Returns:
            Tuple of (text_body, html_body)
        """
        plain_parts = []
        html_parts = []

        def walk(part: Dict[str, Any]):
            mime_type = part.get('mimeType', '')
            body = part.get('body', {})
            data = body.get('data')

            if mime_type == 'text/plain' and data:
                plain_parts.append(self._decode_base64url(data))
            elif mime_type == 'text/html' and data:
                html_parts.append(self._decode_base64url(data))

            # Recurse into multipart
            for child in part.get('parts', []) or []:
                walk(child)

        walk(payload)

        text_body = "\n".join(plain_parts) if plain_parts else None
        html_body = "\n".join(html_parts) if html_parts else None

        return text_body, html_body

    def _extract_attachment_metadata(
        self,
        message_id: str,
        payload: Dict[str, Any],
    ) -> List[EmailAttachment]:
        """
        Extract attachment metadata from message payload.

        Does not download attachment data - use download_attachment() for that.

        Returns:
            List of EmailAttachment objects (without data)
        """
        attachments = []

        def walk(part: Dict[str, Any]):
            filename = part.get('filename', '')
            body = part.get('body', {})

            # Check if this part is an attachment
            if filename and body.get('attachmentId'):
                attachments.append(EmailAttachment(
                    filename=filename,
                    mime_type=part.get('mimeType', 'application/octet-stream'),
                    size=body.get('size', 0),
                    attachment_id=body['attachmentId'],
                ))

            # Recurse into multipart
            for child in part.get('parts', []) or []:
                walk(child)

        walk(payload)
        return attachments

    def download_attachment(
        self,
        message_id: str,
        attachment: EmailAttachment,
    ) -> bytes:
        """
        Download attachment data.

        Args:
            message_id: Gmail message ID
            attachment: EmailAttachment object with attachment_id

        Returns:
            Raw attachment bytes
        """
        self._ensure_authenticated()

        result = self.service.users().messages().attachments().get(
            userId=self.user_id,
            messageId=message_id,
            id=attachment.attachment_id,
        ).execute()

        data = result.get('data', '')
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)

    def save_attachment(
        self,
        message_id: str,
        attachment: EmailAttachment,
        output_dir: str,
    ) -> Path:
        """
        Download and save attachment to disk.

        Args:
            message_id: Gmail message ID
            attachment: EmailAttachment object
            output_dir: Directory to save attachment

        Returns:
            Path to saved file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate safe filename
        safe_filename = "".join(
            c if c.isalnum() or c in '.-_' else '_'
            for c in attachment.filename
        )
        file_path = output_path / safe_filename

        # Handle duplicates
        counter = 1
        while file_path.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            file_path = output_path / f"{stem}_{counter}{suffix}"
            counter += 1

        # Download and save
        data = self.download_attachment(message_id, attachment)
        file_path.write_bytes(data)

        logger.info(f"Saved attachment: {file_path}")
        return file_path

    def get_labels(self) -> List[Dict[str, str]]:
        """Get all labels for the account."""
        self._ensure_authenticated()
        results = self.service.users().labels().list(userId=self.user_id).execute()
        return results.get('labels', [])


# Convenience function for quick setup
def create_gmail_client(token_file: str = DEFAULT_TOKEN_FILE) -> GmailClient:
    """
    Create and authenticate a Gmail client.

    Args:
        token_file: Path to token pickle file

    Returns:
        Authenticated GmailClient
    """
    client = GmailClient(token_file=token_file)
    client.authenticate()
    return client


if __name__ == "__main__":
    # Example usage / test
    import sys
    from datetime import timedelta

    logging.basicConfig(level=logging.INFO)

    # Create client and authenticate
    client = create_gmail_client()

    # Fetch recent emails from Primary inbox
    since = datetime.now() - timedelta(days=7)
    print(f"\nFetching emails since {since}...\n")

    for email in client.fetch_emails(
        since=since,
        max_results=10,
        category="primary",
    ):
        print(f"From: {email.from_address}")
        print(f"Subject: {email.subject}")
        print(f"Date: {email.date}")
        print(f"Attachments: {len(email.attachments)}")
        for att in email.attachments:
            print(f"  - {att.filename} ({att.mime_type}, {att.size} bytes)")
        print(f"Link: {email.permalink}")
        print("-" * 50)
