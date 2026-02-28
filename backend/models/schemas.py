"""
PromptShield Gateway — Pydantic Schemas
Request/response models for all API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Enums ──────────────────────────────────────────────────────────────

class ThreatLevel(str, Enum):
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


class PIIEntityType(str, Enum):
    EMAIL = "EMAIL_ADDRESS"
    PHONE = "PHONE_NUMBER"
    SSN = "US_SSN"
    CREDIT_CARD = "CREDIT_CARD"
    IP_ADDRESS = "IP_ADDRESS"
    API_KEY = "API_KEY"
    AWS_KEY = "AWS_KEY"
    DATE_OF_BIRTH = "DATE_TIME"
    NAME = "PERSON"
    ADDRESS = "LOCATION"
    PASSWORD = "PASSWORD"
    AADHAAR = "AADHAAR"
    PASSPORT = "US_PASSPORT"
    MEDICAL_ID = "MEDICAL_LICENSE"
    STUDENT_ID = "STUDENT_ID"
    US_DRIVER_LICENSE = "US_DRIVER_LICENSE"
    US_BANK_NUMBER = "US_BANK_NUMBER"
    IBAN_CODE = "IBAN_CODE"
    CRYPTO = "CRYPTO"
    NRP = "NRP"
    URL = "URL"


# ── PII Detection ─────────────────────────────────────────────────────

class PIIEntity(BaseModel):
    entity_type: str
    original: str
    redacted: str
    confidence: float = Field(ge=0, le=1)
    start: int
    end: int
    category: Optional[str] = None  # Identity, Financial/ID, Academic


class PIIScanResult(BaseModel):
    pii_found: bool
    entity_count: int
    entities: list[PIIEntity]
    sanitized_text: str
    original_text: str


# ── Injection Detection ───────────────────────────────────────────────

class InjectionPattern(BaseModel):
    pattern_name: str
    category: str  # OWASP LLM category
    description: str
    severity: str  # low, medium, high, critical
    matched_text: Optional[str] = None


class InjectionScanResult(BaseModel):
    threat_level: ThreatLevel
    threat_score: int = Field(ge=0, le=100)
    patterns_matched: list[InjectionPattern]
    recommendation: str
    details: str


# ── API Request / Response ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=10000)
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    system_prompt: Optional[str] = None


class ScanRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)


class SecurityMetadata(BaseModel):
    pii_scan: PIIScanResult
    injection_scan: InjectionScanResult
    processing_time_ms: float


# ── Token Economics ────────────────────────────────────────────────────

class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


# ── Explainable Rejections ─────────────────────────────────────────────

class BlockReason(BaseModel):
    code: str                # e.g. "PII_DETECTED", "INJECTION_BLOCKED"
    entity_type: Optional[str] = None  # e.g. "ROLL_NUMBER", "US_SSN"
    message: str             # Human-readable message
    severity: str = "high"   # low, medium, high, critical


class ChatResponse(BaseModel):
    response: Optional[str] = None
    blocked: bool = False
    block_reasons: list[BlockReason] = []
    security: SecurityMetadata
    token_usage: Optional[TokenUsage] = None


class ScanResponse(BaseModel):
    pii_scan: PIIScanResult
    injection_scan: InjectionScanResult
    overall_risk: ThreatLevel
    processing_time_ms: float


# ── Dashboard ──────────────────────────────────────────────────────────

class ThreatLogEntry(BaseModel):
    timestamp: str
    source_ip: str = "campus-portal"
    prompt_preview: str
    pii_count: int
    injection_score: int
    threat_level: ThreatLevel
    patterns: list[str]
    action: str  # "allowed", "sanitized", "blocked"


class DashboardStats(BaseModel):
    institution_name: str = "University Tech"
    total_requests: int
    blocked_requests: int
    sanitized_requests: int
    safe_requests: int
    total_pii_detected: int
    total_injections_detected: int
    top_pii_types: dict[str, int]
    top_injection_patterns: dict[str, int]
    threat_timeline: list[dict]
    block_rate_percent: float
    avg_threat_score: float
    total_estimated_cost_usd: float = 0.0

