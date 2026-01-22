"""Confidence scoring utilities."""

from typing import List, Dict, Any


def calculate_mapping_confidence(
    base_method: str,
    data_type_matches: bool = False,
    sample_valid: bool = False,
    high_null_rate: bool = False,
    generic_name: bool = False,
    multiple_candidates: bool = False
) -> float:
    """
    Calculate confidence score for a field mapping.

    Args:
        base_method: The mapping method used (exact_name_match, fuzzy_name_match, etc.)
        data_type_matches: Whether data type matches expected type
        sample_valid: Whether sample values are valid for this field
        high_null_rate: Whether field has high null rate (>20%)
        generic_name: Whether column name is generic/ambiguous
        multiple_candidates: Whether multiple close match candidates exist

    Returns:
        Confidence score between 0.0 and 1.0
    """
    # Base confidence by method
    method_confidence = {
        'exact_name_match': 0.95,
        'fuzzy_name_match': 0.75,
        'semantic_match': 0.60,
        'derived_field': 0.70,
        'passthrough': 0.80,
        'passthrough_with_cleanup': 0.85,
        'unpivot': 0.95,
        'constant': 1.0,
        'null': 1.0,
    }

    base = method_confidence.get(base_method, 0.50)

    # Adjustments
    adjustments = 0.0

    if data_type_matches:
        adjustments += 0.10

    if sample_valid:
        adjustments += 0.05

    if high_null_rate:
        adjustments -= 0.15

    if generic_name:
        adjustments -= 0.10

    if multiple_candidates:
        adjustments -= 0.20

    # Final confidence (clamped to 0-1)
    final = base + adjustments
    return max(0.0, min(1.0, final))


def calculate_overall_confidence(
    mapping_confidence: float,
    error_rate: float,
    warning_rate: float
) -> float:
    """
    Calculate overall run confidence.

    Args:
        mapping_confidence: Minimum confidence from all mappings
        error_rate: Proportion of rows with errors (0.0 to 1.0)
        warning_rate: Proportion of rows with warnings (0.0 to 1.0)

    Returns:
        Overall confidence score between 0.0 and 1.0
    """
    quality_confidence = 1.0 - (error_rate + warning_rate * 0.5)
    quality_confidence = max(0.0, min(1.0, quality_confidence))

    # Overall is the minimum of mapping and quality confidence
    return min(mapping_confidence, quality_confidence)


def should_require_review(
    overall_confidence: float,
    mapping_confidence: float,
    error_rate: float,
    warning_rate: float,
    is_new_partner: bool = False,
    is_first_run: bool = False,
    config: Dict[str, Any] = None
) -> tuple[bool, List[str]]:
    """
    Determine if human review is required.

    Args:
        overall_confidence: Overall confidence score
        mapping_confidence: Mapping confidence score
        error_rate: Error rate (0.0 to 1.0)
        warning_rate: Warning rate (0.0 to 1.0)
        is_new_partner: Whether partner is not in known list
        is_first_run: Whether this is first run for this source
        config: Configuration dict

    Returns:
        Tuple of (review_required: bool, reasons: List[str])
    """
    if config is None:
        config = {
            'require_review_confidence_threshold': 0.6,
            'max_error_rate_before_fail': 0.05,
            'max_warning_rate_before_review': 0.20,
        }

    review_required = False
    reasons = []

    # Low overall confidence
    threshold = config.get('require_review_confidence_threshold', 0.6)
    if overall_confidence < threshold:
        review_required = True
        reasons.append(f"Overall confidence ({overall_confidence:.2f}) below threshold ({threshold})")

    # High error rate
    max_error_rate = config.get('max_error_rate_before_fail', 0.05)
    if error_rate > max_error_rate:
        review_required = True
        reasons.append(f"Error rate ({error_rate*100:.1f}%) exceeds threshold ({max_error_rate*100:.1f}%)")

    # High warning rate
    max_warning_rate = config.get('max_warning_rate_before_review', 0.20)
    if warning_rate > max_warning_rate:
        review_required = True
        reasons.append(f"Warning rate ({warning_rate*100:.1f}%) exceeds threshold ({max_warning_rate*100:.1f}%)")

    # New partner
    if is_new_partner and config.get('require_review_for_new_partners', True):
        review_required = True
        reasons.append("New partner not in known partners list")

    # First run
    if is_first_run:
        review_required = True
        reasons.append("First run for this data source")

    return review_required, reasons
