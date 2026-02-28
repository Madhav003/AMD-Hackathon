"""
PromptShield Gateway - Settings Routes
Endpoints for managing gateway configuration from the frontend.
"""
import json
import os
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/api/v1", tags=["settings"])

SETTINGS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "settings.json",
)


# ── Pydantic Models ────────────────────────────────────────────────────

class CustomPattern(BaseModel):
    name: str
    pattern: str  # Human-readable format like "nnlllnnn"
    label: str
    category: str = "Academic"


class SettingsRequest(BaseModel):
    institution_name: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_history_length: Optional[int] = Field(default=None, ge=2, le=100)
    block_strictness: Optional[str] = None
    max_pii_before_block: Optional[int] = Field(default=None, ge=1, le=20)
    custom_id_patterns: Optional[list[CustomPattern]] = None


class SettingsResponse(BaseModel):
    institution_name: str
    system_prompt: str
    temperature: float
    max_history_length: int
    block_strictness: str
    max_pii_before_block: int
    custom_id_patterns: list[CustomPattern]


# ── Helper Functions ───────────────────────────────────────────────────

def pattern_to_regex(pattern: str) -> str:
    """
    Convert human-friendly pattern to regex.
    n = digit (0-9)
    l = letter (a-zA-Z)
    * = any character
    Other characters are escaped and matched literally.
    
    Example: "nnlllnnn" -> r"\b\d{2}[a-zA-Z]{3}\d{3}\b"
    """
    result = []
    i = 0
    while i < len(pattern):
        char = pattern[i]
        
        # Count consecutive same characters for grouping
        count = 1
        while i + count < len(pattern) and pattern[i + count] == char:
            count += 1
        
        if char == 'n':
            if count == 1:
                result.append(r"\d")
            else:
                result.append(rf"\d{{{count}}}")
        elif char == 'l':
            if count == 1:
                result.append(r"[a-zA-Z]")
            else:
                result.append(rf"[a-zA-Z]{{{count}}}")
        elif char == '*':
            if count == 1:
                result.append(r".")
            else:
                result.append(rf".{{{count}}}")
        else:
            # Escape special regex characters and repeat
            escaped = re.escape(char)
            result.append(escaped * count)
        
        i += count
    
    return r"\b" + "".join(result) + r"\b"


def generate_example(pattern: str) -> str:
    """Generate an example string from a pattern."""
    import random
    import string
    
    result = []
    for char in pattern:
        if char == 'n':
            result.append(random.choice(string.digits))
        elif char == 'l':
            result.append(random.choice(string.ascii_lowercase))
        elif char == '*':
            result.append(random.choice(string.ascii_letters + string.digits))
        else:
            result.append(char)
    return "".join(result)


def load_settings() -> dict:
    """Load settings from JSON file."""
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    return {}


def save_settings(settings: dict):
    """Save settings to JSON file."""
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=4)


# ── Endpoints ──────────────────────────────────────────────────────────

@router.get("/settings/full", response_model=SettingsResponse)
async def get_full_settings():
    """Get all configurable settings."""
    cfg = load_settings()
    
    # Parse existing custom_patterns back to our format
    custom_id_patterns = []
    
    # Handle roll_number as a custom pattern if it exists
    if cfg.get("roll_number_regex"):
        # Try to find the original pattern format (stored separately)
        custom_id_patterns.append(CustomPattern(
            name=cfg.get("roll_number_label", "Roll Number"),
            pattern=cfg.get("roll_number_pattern", ""),  # Original pattern format
            label=cfg.get("roll_number_label", "ROLL_NUMBER"),
            category="Academic"
        ))
    
    # Add other custom patterns
    for cp in cfg.get("custom_id_patterns", []):
        custom_id_patterns.append(CustomPattern(
            name=cp.get("name", ""),
            pattern=cp.get("pattern", ""),
            label=cp.get("label", ""),
            category=cp.get("category", "Academic")
        ))
    
    return SettingsResponse(
        institution_name=cfg.get("institution_name", "University Tech"),
        system_prompt=cfg.get("system_prompt", 
            "You are PromptShield AI, a helpful and secure academic assistant. "
            "You provide accurate, educational responses while maintaining user privacy. "
            "Be concise but thorough."),
        temperature=cfg.get("temperature", 0.7),
        max_history_length=cfg.get("max_history_length", 20),
        block_strictness=cfg.get("block_strictness", "high"),
        max_pii_before_block=cfg.get("max_pii_before_block", 5),
        custom_id_patterns=custom_id_patterns,
    )


@router.put("/settings/full")
async def update_settings(request: SettingsRequest):
    """Update settings and trigger PII detector reload."""
    cfg = load_settings()
    
    # Update basic settings
    if request.institution_name is not None:
        cfg["institution_name"] = request.institution_name
    if request.system_prompt is not None:
        cfg["system_prompt"] = request.system_prompt
    if request.temperature is not None:
        cfg["temperature"] = request.temperature
    if request.max_history_length is not None:
        cfg["max_history_length"] = request.max_history_length
    if request.block_strictness is not None:
        if request.block_strictness not in ["low", "medium", "high"]:
            raise HTTPException(status_code=400, detail="Invalid block_strictness value")
        cfg["block_strictness"] = request.block_strictness
    if request.max_pii_before_block is not None:
        cfg["max_pii_before_block"] = request.max_pii_before_block
    
    # Handle custom ID patterns
    if request.custom_id_patterns is not None:
        custom_patterns_for_pii = []
        custom_id_storage = []
        
        for i, cp in enumerate(request.custom_id_patterns):
            if not cp.pattern.strip():
                continue
                
            regex = pattern_to_regex(cp.pattern)
            example = generate_example(cp.pattern)
            
            # Store the original pattern format for editing later
            custom_id_storage.append({
                "name": cp.name or f"Custom ID {i+1}",
                "pattern": cp.pattern,
                "label": cp.label or f"CUSTOM_ID_{i+1}",
                "category": cp.category,
            })
            
            # Generate the regex pattern for PII detection
            custom_patterns_for_pii.append({
                "name": cp.name or f"Custom ID {i+1}",
                "regex": regex,
                "label": cp.label or f"CUSTOM_ID_{i+1}",
                "redact_tag": f"[REDACTED {cp.label or f'CUSTOM_ID_{i+1}'}]",
                "category": cp.category,
            })
        
        # Store both the original patterns and the generated regex patterns
        cfg["custom_id_patterns"] = custom_id_storage
        
        # Merge with existing custom_patterns (preserve non-ID patterns)
        existing_patterns = [p for p in cfg.get("custom_patterns", []) 
                           if not p.get("label", "").startswith("CUSTOM_ID")]
        cfg["custom_patterns"] = existing_patterns + custom_patterns_for_pii
        
        # Clear old roll_number format (migrated to custom_id_patterns)
        if "roll_number_regex" in cfg:
            del cfg["roll_number_regex"]
        if "roll_number_label" in cfg:
            del cfg["roll_number_label"]
        if "roll_number_pattern" in cfg:
            del cfg["roll_number_pattern"]
    
    save_settings(cfg)
    
    # Reload PII detector to pick up new patterns
    try:
        from engines.pii_detector import reload_detector
        reload_detector()
    except Exception:
        pass  # If reload isn't implemented yet, that's okay
    
    return {
        "status": "success",
        "message": "Settings saved successfully",
        "patterns_updated": len(request.custom_id_patterns) if request.custom_id_patterns else 0,
    }


@router.post("/settings/pattern/preview")
async def preview_pattern(pattern: str):
    """Preview what a pattern will match."""
    try:
        regex = pattern_to_regex(pattern)
        examples = [generate_example(pattern) for _ in range(3)]
        return {
            "pattern": pattern,
            "regex": regex,
            "examples": examples,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid pattern: {str(e)}")


@router.post("/settings/reset")
async def reset_settings():
    """Reset settings to defaults."""
    default_settings = {
        "institution_name": "University Tech",
        "system_prompt": (
            "You are PromptShield AI, a helpful and secure academic assistant. "
            "You provide accurate, educational responses while maintaining user privacy. "
            "Be concise but thorough."
        ),
        "temperature": 0.7,
        "max_history_length": 20,
        "block_strictness": "high",
        "max_pii_before_block": 5,
        "custom_id_patterns": [],
        "custom_patterns": [],
        "token_costs": {
            "prompt_cost_per_1k": 0.0005,
            "completion_cost_per_1k": 0.0015,
            "currency": "USD",
            "monthly_budget_limit": 50.00
        },
        "rate_limit": {
            "requests_per_minute": 5,
            "burst_limit": 10
        }
    }
    save_settings(default_settings)
    
    # Reload PII detector
    try:
        from engines.pii_detector import reload_detector
        reload_detector()
    except Exception:
        pass
    
    return {"status": "success", "message": "Settings reset to defaults"}
