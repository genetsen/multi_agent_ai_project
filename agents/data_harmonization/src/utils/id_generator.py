"""ID generation utilities."""

import uuid
from datetime import datetime


def generate_run_id(prefix: str = "dh") -> str:
    """
    Generate a unique run ID.

    Args:
        prefix: Prefix for the ID (default: "dh" for data harmonization)

    Returns:
        Run ID in format: {prefix}-{date}-{short_uuid}
    """
    date_str = datetime.now().strftime("%Y%m%d")
    short_uuid = str(uuid.uuid4())[:8]
    return f"{prefix}-{date_str}-{short_uuid}"


def generate_review_id(prefix: str = "rv") -> str:
    """
    Generate a unique review item ID.

    Args:
        prefix: Prefix for the ID (default: "rv" for review)

    Returns:
        Review ID in format: {prefix}-dh-{date}-{counter}
    """
    date_str = datetime.now().strftime("%Y%m%d")
    short_uuid = str(uuid.uuid4())[:6]
    return f"{prefix}-dh-{date_str}-{short_uuid}"


def generate_record_id(email_id: str, row_num: int, metric_name: str) -> str:
    """
    Generate source_record_id for lineage tracking.

    Args:
        email_id: Source email ID
        row_num: Row number in source file
        metric_name: Name of the metric

    Returns:
        Record ID in format: {email_id}:{row_num}:{metric_name}
    """
    return f"{email_id}:{row_num}:{metric_name}"
