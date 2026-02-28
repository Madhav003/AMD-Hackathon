"""
PromptShield Gateway - Dashboard Routes
Endpoints for threat statistics, logs, system health, and token economics.
"""
import json
import os
from fastapi import APIRouter, Query
from models.schemas import DashboardStats, ThreatLogEntry
from storage.threat_logger import threat_logger
from engines.threat_intel import threat_intel

router = APIRouter(prefix="/api/v1", tags=["dashboard"])

# Load institution name from settings.json
_settings_cfg = {}
_settings_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "settings.json",
)
if os.path.exists(_settings_path):
    with open(_settings_path, "r") as f:
        _settings_cfg = json.load(f)


@router.get("/stats", response_model=DashboardStats)
async def get_stats():
    """Get aggregated threat dashboard statistics."""
    stats = threat_logger.get_stats()
    # Inject institution name and cost from settings
    stats.institution_name = _settings_cfg.get("institution_name", "University Tech")
    try:
        from routes.proxy import get_total_cost
        stats.total_estimated_cost_usd = get_total_cost()
    except Exception:
        pass
    return stats


@router.get("/threats", response_model=list[ThreatLogEntry])
async def get_threats(limit: int = Query(default=20, ge=1, le=100)):
    """Get recent threat log entries."""
    return threat_logger.get_recent_threats(limit=limit)


@router.get("/health")
async def health_check():
    """System health check endpoint."""
    stats = threat_logger.get_stats()
    try:
        from routes.proxy import get_total_cost
        cost = get_total_cost()
    except Exception:
        cost = 0.0
    return {
        "status": "operational",
        "service": "PromptShield Gateway",
        "institution": _settings_cfg.get("institution_name", "University Tech"),
        "version": "2.0.0",
        "engines": {
            "pii_detector": "active (Presidio)",
            "injection_detector": "active (16+ patterns)",
            "threat_intel": "active (OWASP LLM Top 10)",
            "token_economics": "active",
            "dynamic_patterns": f"{len(_settings_cfg.get('custom_patterns', []))} custom patterns loaded",
        },
        "total_requests_processed": stats.total_requests,
        "threats_blocked": stats.blocked_requests,
        "total_estimated_cost_usd": cost,
        "block_strictness": _settings_cfg.get("block_strictness", "medium"),
    }


@router.get("/settings")
async def get_settings():
    """Get current admin settings (non-sensitive)."""
    return {
        "institution_name": _settings_cfg.get("institution_name", "University Tech"),
        "block_strictness": _settings_cfg.get("block_strictness", "medium"),
        "roll_number_format": _settings_cfg.get("roll_number_regex", "N/A"),
        "custom_patterns_count": len(_settings_cfg.get("custom_patterns", [])),
        "token_costs": _settings_cfg.get("token_costs", {}),
        "rate_limit": _settings_cfg.get("rate_limit", {}),
    }


@router.get("/owasp")
async def get_owasp_categories():
    """Get OWASP Top 10 for LLMs reference data."""
    return threat_intel.get_all_categories()


@router.post("/reset")
async def reset_stats():
    """Reset all statistics (for demo purposes)."""
    threat_logger.reset()
    return {"status": "reset", "message": "All statistics have been cleared."}
