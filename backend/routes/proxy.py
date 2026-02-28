"""
PromptShield Gateway - Proxy Routes
Smart demo mode, explainable rejections, token economics.
"""
import json
import os
import time
from fastapi import APIRouter
from config import settings
from models.schemas import (
    ChatRequest, ChatResponse, ScanRequest, ScanResponse,
    SecurityMetadata, ThreatLevel, TokenUsage, BlockReason,
)
from engines.pii_detector import pii_detector
from engines.injection_detector import injection_detector
from storage.threat_logger import threat_logger

router = APIRouter(prefix="/api/v1", tags=["proxy"])

# ── Load settings.json for token costs ─────────────────────────────────
_settings_cfg = {}
_settings_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "settings.json",
)
if os.path.exists(_settings_path):
    with open(_settings_path, "r") as f:
        _settings_cfg = json.load(f)

TOKEN_COSTS = _settings_cfg.get("token_costs", {})
BLOCK_STRICTNESS = _settings_cfg.get("block_strictness", "medium")

# ── Cumulative cost tracker (in-memory) ────────────────────────────────
_total_cost = 0.0


def _estimate_tokens(text):
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def _calculate_cost(prompt_tokens, completion_tokens):
    """Calculate estimated cost based on settings.json rates."""
    prompt_rate = TOKEN_COSTS.get("prompt_cost_per_1k", 0.0005)
    completion_rate = TOKEN_COSTS.get("completion_cost_per_1k", 0.0015)
    cost = (prompt_tokens / 1000 * prompt_rate) + (completion_tokens / 1000 * completion_rate)
    return round(cost, 6)


def _build_block_reasons(pii_result, injection_result):
    """Build structured, explainable block/warning reasons."""
    reasons = []

    # Injection-based blocks
    if injection_result.threat_level == ThreatLevel.BLOCKED:
        for p in injection_result.patterns_matched[:3]:
            reasons.append(BlockReason(
                code="INJECTION_BLOCKED",
                entity_type=p.pattern_name,
                message=f"Prompt injection detected: {p.pattern_name}. {p.description}",
                severity=p.severity,
            ))

    # PII-based warnings/blocks
    if pii_result.pii_found:
        pii_types = set(e.entity_type for e in pii_result.entities)
        for pt in pii_types:
            count = sum(1 for e in pii_result.entities if e.entity_type == pt)
            reasons.append(BlockReason(
                code="PII_DETECTED",
                entity_type=pt,
                message=f"PII detected: {count} {pt} instance(s) found and redacted. Please remove sensitive data.",
                severity="medium",
            ))

    # High strictness: block if too many PII entities
    max_pii = _settings_cfg.get("max_pii_before_block", 5)
    if BLOCK_STRICTNESS == "high" and pii_result.entity_count >= max_pii:
        reasons.append(BlockReason(
            code="PII_OVERLOAD",
            message=f"Too many PII entities ({pii_result.entity_count}) detected. Blocked under high-strictness policy.",
            severity="critical",
        ))

    return reasons


def _generate_demo_response(safe_prompt, pii_result, injection_result):
    """Generate a smart, context-aware demo response (no API needed)."""
    prompt_lower = safe_prompt.lower()

    # Academic Q&A responses
    if any(kw in prompt_lower for kw in ["machine learning", "ml", "deep learning"]):
        return ("Machine Learning is a subset of artificial intelligence where "
                "systems learn from data to improve their performance without "
                "being explicitly programmed. Key types include supervised learning "
                "(labeled data), unsupervised learning (pattern discovery), and "
                "reinforcement learning (reward-based). Popular applications include "
                "image recognition, natural language processing, and recommendation systems.")

    if any(kw in prompt_lower for kw in ["what is ai", "artificial intelligence"]):
        return ("Artificial Intelligence (AI) is the simulation of human intelligence "
                "by machines. It encompasses techniques like machine learning, neural "
                "networks, and natural language processing to enable computers to learn, "
                "reason, and make decisions. Modern AI powers everything from virtual "
                "assistants to autonomous vehicles.")

    if any(kw in prompt_lower for kw in ["python", "programming", "code", "function"]):
        return ("Python is a high-level, interpreted programming language known "
                "for its simplicity and readability. It's widely used in web "
                "development (Django, Flask), data science (Pandas, NumPy), "
                "machine learning (TensorFlow, PyTorch), and automation. Its "
                "extensive library ecosystem makes it ideal for rapid prototyping.")

    if any(kw in prompt_lower for kw in ["math", "calculus", "algebra", "equation"]):
        return ("Mathematics is the foundation of computer science and engineering. "
                "Key areas include linear algebra (matrices, vectors), calculus "
                "(derivatives, integrals), probability and statistics (Bayesian "
                "inference, distributions), and discrete math (graph theory, "
                "combinatorics). Each plays a critical role in algorithm design.")

    if any(kw in prompt_lower for kw in ["history", "world war", "civilization"]):
        return ("History is the study of past events, cultures, and civilizations. "
                "Understanding history helps us learn from past mistakes and "
                "appreciate the evolution of human societies, technologies, and "
                "political systems. Key periods include ancient civilizations, "
                "the Renaissance, the Industrial Revolution, and the Digital Age.")

    if any(kw in prompt_lower for kw in ["hello", "hi", "hey", "good morning"]):
        return ("Hello! I'm PromptShield AI, your secure academic assistant. "
                "I can help you with study questions while protecting your "
                "privacy. All messages are scanned for PII and injection "
                "attacks before processing. How can I help you today?")

    if pii_result.pii_found:
        return (f"Your message contained {pii_result.entity_count} piece(s) of "
                f"sensitive data that were automatically redacted for your safety. "
                f"The sanitized version of your prompt is: \"{safe_prompt}\". "
                f"Please rephrase without including personal information.")

    # Generic academic response
    return (f"Thank you for your question! As PromptShield AI, I've verified "
            f"your prompt is clean and safe (threat score: "
            f"{injection_result.threat_score}/100). In a production deployment "
            f"with a connected LLM, this sanitized prompt would be forwarded "
            f"for a full AI response. Your data stays protected throughout.")


@router.post("/chat", response_model=ChatResponse)
async def chat_proxy(request: ChatRequest):
    """
    Main proxy endpoint.
    1. Scan for PII -> 2. Scan for injection -> 3. Respond (demo or Gemini).
    """
    global _total_cost
    start_time = time.time()

    # -- Step 1: PII Scan --
    pii_result = pii_detector.scan(request.prompt)

    # -- Step 2: Injection Scan --
    injection_result = injection_detector.scan(request.prompt)

    processing_time = round((time.time() - start_time) * 1000, 2)

    security = SecurityMetadata(
        pii_scan=pii_result,
        injection_scan=injection_result,
        processing_time_ms=processing_time,
    )

    # -- Build explainable block reasons --
    block_reasons = _build_block_reasons(pii_result, injection_result)

    # Determine action
    if injection_result.threat_level == ThreatLevel.BLOCKED:
        action = "blocked"
    elif pii_result.pii_found:
        action = "sanitized"
    else:
        action = "allowed"

    # -- Token economics (estimate) --
    prompt_tokens = _estimate_tokens(request.prompt)
    completion_tokens = 0

    # Log the threat
    threat_logger.log(
        prompt=request.prompt,
        pii_count=pii_result.entity_count,
        pii_types=[e.entity_type for e in pii_result.entities],
        injection_score=injection_result.threat_score,
        threat_level=injection_result.threat_level,
        patterns=[p.pattern_name for p in injection_result.patterns_matched],
        action=action,
    )

    # -- Step 3: Block if threat level is too high --
    if injection_result.threat_level == ThreatLevel.BLOCKED:
        # Explainable rejection
        reasons_text = " | ".join(r.message for r in block_reasons[:3])
        return ChatResponse(
            response=f"Request blocked by PromptShield. {reasons_text}",
            blocked=True,
            block_reasons=block_reasons,
            security=security,
            token_usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                estimated_cost_usd=0.0,
            ),
        )

    # -- Step 4: Generate response --
    safe_prompt = pii_result.sanitized_text

    # Check if Gemini API is available
    use_gemini = (
        settings.GEMINI_API_KEY
        and not settings.GEMINI_API_KEY.startswith("your-")
        and len(settings.GEMINI_API_KEY) > 10
    )

    if use_gemini:
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            model_name = request.model or settings.GEMINI_MODEL
            # Ensure model name has 'models/' prefix
            if not model_name.startswith("models/"):
                model_name = f"models/{model_name}"

            full_prompt = safe_prompt
            if request.system_prompt:
                full_prompt = f"[System]: {request.system_prompt}\n\n[User]: {safe_prompt}"

            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config={
                    "temperature": request.temperature or 0.7,
                },
            )
            response_text = response.text
            completion_tokens = _estimate_tokens(response_text)

        except Exception as e:
            # Fall back to demo mode on API error
            response_text = _generate_demo_response(safe_prompt, pii_result, injection_result)
            completion_tokens = _estimate_tokens(response_text)
    else:
        # Demo mode
        response_text = _generate_demo_response(safe_prompt, pii_result, injection_result)
        completion_tokens = _estimate_tokens(response_text)

    # Calculate cost
    cost = _calculate_cost(prompt_tokens, completion_tokens)
    _total_cost += cost

    processing_time = round((time.time() - start_time) * 1000, 2)
    security.processing_time_ms = processing_time

    return ChatResponse(
        response=response_text,
        blocked=False,
        block_reasons=block_reasons,
        security=security,
        token_usage=TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=cost,
        ),
    )


@router.post("/scan", response_model=ScanResponse)
async def scan_only(request: ScanRequest):
    """
    Scan-only endpoint. Returns PII and injection analysis
    without forwarding to any LLM.
    """
    start_time = time.time()

    pii_result = pii_detector.scan(request.text)
    injection_result = injection_detector.scan(request.text)

    processing_time = round((time.time() - start_time) * 1000, 2)

    # Determine overall risk
    if injection_result.threat_level == ThreatLevel.BLOCKED:
        overall_risk = ThreatLevel.BLOCKED
    elif (injection_result.threat_level == ThreatLevel.SUSPICIOUS
          or pii_result.entity_count > 3):
        overall_risk = ThreatLevel.SUSPICIOUS
    elif pii_result.pii_found:
        overall_risk = ThreatLevel.SUSPICIOUS
    else:
        overall_risk = ThreatLevel.SAFE

    # Log
    threat_logger.log(
        prompt=request.text,
        pii_count=pii_result.entity_count,
        pii_types=[e.entity_type for e in pii_result.entities],
        injection_score=injection_result.threat_score,
        threat_level=injection_result.threat_level,
        patterns=[p.pattern_name for p in injection_result.patterns_matched],
        action="scan-only",
    )

    return ScanResponse(
        pii_scan=pii_result,
        injection_scan=injection_result,
        overall_risk=overall_risk,
        processing_time_ms=processing_time,
    )


def get_total_cost():
    """Return cumulative API cost for the dashboard."""
    return round(_total_cost, 4)
