"""
Data models and schemas for the Data Harmonization Agent.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# INPUT CONTRACTS
# ============================================================================

class RawSource(BaseModel):
    """Single raw data source to be harmonized."""
    source_system: str = Field(..., description="Origin system (email, google_sheets, csv, s3, sftp, bigquery)")
    source_location: str = Field(..., description="Path or URL to the data")
    data_type: Optional[str] = Field(None, description="csv, xlsx, google_sheets, etc.")
    partner_name: Optional[str] = Field(None, description="Expected partner name (if known)")
    received_at: Optional[str] = Field(None, description="When data was received")
    expected_granularity: Optional[str] = Field(None, description="daily, weekly, monthly")
    expected_metrics: Optional[List[str]] = Field(None, description="List of expected metric names")


class SourceEmail(BaseModel):
    """Email metadata when source is email."""
    id: str
    subject: str
    from_: str = Field(..., alias="from")
    to: Optional[str] = None
    date: str
    permalink: Optional[str] = None


class HarmonizationInput(BaseModel):
    """Complete input contract for Data Harmonization Agent."""
    run_id: Optional[str] = Field(None, description="Unique run identifier")
    source_email: Optional[SourceEmail] = Field(None, description="Email metadata if from email")
    raw_sources: List[RawSource] = Field(..., description="List of raw data sources to harmonize")
    config: Optional[Dict[str, Any]] = Field(None, description="Optional configuration overrides")


# ============================================================================
# STAGE OUTPUTS
# ============================================================================

class IngestionMetadata(BaseModel):
    """Metadata from source ingestion."""
    rows_read: int
    columns_read: int
    encoding: str
    file_size_bytes: Optional[int] = None
    header_row: Optional[int] = None
    metadata_rows_skipped: Optional[int] = None
    warnings: List[str] = Field(default_factory=list)


class ColumnProfile(BaseModel):
    """Profile of a single column."""
    column_name: str
    data_type: str
    null_count: int
    null_percentage: float
    unique_count: int
    cardinality: Literal["high", "medium", "low"]
    sample_values: List[Any]
    semantic_type: Optional[str] = None
    semantic_confidence: Optional[float] = None
    semantic_reasoning: Optional[List[str]] = None


class TransformParams(BaseModel):
    """Parameters for a specific transform."""
    params: Dict[str, Any] = Field(default_factory=dict)


class FieldMapping(BaseModel):
    """Mapping from raw column to canonical field."""
    canonical_field: str
    source_column: Optional[str] = None
    source_columns: Optional[List[str]] = None
    mapping_method: str
    transform: Optional[str] = None
    transform_params: Optional[Dict[str, Any]] = None
    confidence: float
    reasoning: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    human_review_required: bool = False
    review_reason: Optional[str] = None
    alternatives: Optional[List[Dict[str, Any]]] = None


class ValidationResult(BaseModel):
    """Result from a single validation rule."""
    rule_id: str
    rule_name: str
    severity: Literal["fail", "warn"]
    passed: bool
    rows_affected: int = 0
    message: Optional[str] = None
    recommendation: Optional[str] = None


class ReviewItem(BaseModel):
    """Item requiring human review."""
    review_id: str
    trigger_reason: str
    description: str
    affected_field: Optional[str] = None
    confidence: Optional[float] = None
    threshold: Optional[float] = None
    proposed_mapping: Optional[Dict[str, Any]] = None
    sample_values: Optional[List[Any]] = None
    recommendations: Optional[List[str]] = None
    reviewer_actions: List[str] = Field(default_factory=lambda: ["approve", "reject", "modify"])


# ============================================================================
# OUTPUT CONTRACTS
# ============================================================================

class ColumnInfo(BaseModel):
    """Information about a column in harmonized table."""
    name: str
    type: str
    null_count: int
    format: Optional[str] = None


class HarmonizedTable(BaseModel):
    """Output harmonized table metadata."""
    schema_version: str = "1.0.0"
    run_id: str
    row_count: int
    columns: List[ColumnInfo]
    data_location: str
    sample_rows: List[Dict[str, Any]] = Field(default_factory=list)


class SchemaMap(BaseModel):
    """Complete schema mapping documentation."""
    schema_version: str = "1.0.0"
    run_id: str
    source_file: str
    source_columns: List[str]
    mappings: List[FieldMapping]
    unmapped_columns: List[Dict[str, Any]] = Field(default_factory=list)
    overall_mapping_confidence: float


class StageResult(BaseModel):
    """Result from a single stage."""
    status: str
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RunLog(BaseModel):
    """Complete execution audit trail."""
    schema_version: str = "1.0.0"
    run_id: str
    agent_name: str = "data_harmonization_agent"
    agent_version: str = "1.0.0"
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    status: str
    input: Dict[str, Any]
    processing_summary: Dict[str, Any]
    stage_results: Dict[str, StageResult]
    overall_confidence: float
    confidence_breakdown: Dict[str, Any]
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    human_review_required: bool
    review_items: List[ReviewItem] = Field(default_factory=list)
    output_artifacts: Dict[str, str]
    next_steps: List[str] = Field(default_factory=list)


class HarmonizationOutput(BaseModel):
    """Complete output from Data Harmonization Agent."""
    harmonized_table: HarmonizedTable
    schema_map: SchemaMap
    run_log: RunLog
