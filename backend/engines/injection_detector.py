"""
PromptShield Gateway — Prompt Injection Detection Engine
Scoring-based detection for jailbreaks, indirect injections,
Unicode smuggling, and role confusion attacks.
Maps to OWASP Top 10 for LLMs categories.
"""
import re
from models.schemas import InjectionScanResult, InjectionPattern, ThreatLevel


class InjectionDetector:
    """
    Multi-layer prompt injection detection with weighted scoring.
    Each detected pattern contributes to a cumulative threat score (0–100).
    """

    def __init__(self):
        self._patterns = self._build_patterns()
        self._indirect_patterns = self._build_indirect_patterns()
        self._unicode_patterns = self._build_unicode_patterns()

    def _build_patterns(self) -> list[dict]:
        """Direct prompt injection / jailbreak patterns."""
        return [
            # ── DAN (Do Anything Now) variants ──
            {
                "name": "DAN Jailbreak",
                "category": "LLM01: Prompt Injection",
                "description": "Attempts to bypass safety via 'Do Anything Now' persona",
                "severity": "critical",
                "score": 40,
                "pattern": re.compile(
                    r'\b(?:DAN|do\s+anything\s+now|DANMode|Developer\s+Mode)\b',
                    re.IGNORECASE
                ),
            },
            # ── "Ignore previous instructions" ──
            {
                "name": "Instruction Override",
                "category": "LLM01: Prompt Injection",
                "description": "Attempts to override system instructions",
                "severity": "critical",
                "score": 35,
                "pattern": re.compile(
                    r'(?:ignore|forget|disregard|override|bypass|skip)\s+'
                    r'(?:all\s+)?(?:previous|prior|above|earlier|system|initial)\s+'
                    r'(?:instructions?|prompts?|rules?|guidelines?|constraints?|directives?)',
                    re.IGNORECASE
                ),
            },
            # ── System prompt extraction ──
            {
                "name": "System Prompt Leak",
                "category": "LLM07: Insecure Plugin Design",
                "description": "Attempts to extract the system prompt",
                "severity": "high",
                "score": 30,
                "pattern": re.compile(
                    r'(?:show|reveal|display|print|output|repeat|echo|tell\s+me)\s+'
                    r'(?:your|the)?\s*(?:system\s+)?'
                    r'(?:prompt|instructions?|initial\s+message|hidden\s+text|rules)',
                    re.IGNORECASE
                ),
            },
            # ── Roleplay escape ──
            {
                "name": "Roleplay Escape",
                "category": "LLM01: Prompt Injection",
                "description": "Uses roleplay to bypass safety guardrails",
                "severity": "high",
                "score": 28,
                "pattern": re.compile(
                    r'(?:you\s+are\s+now|act\s+as|pretend\s+(?:to\s+be|you\s+are)|'
                    r'roleplay\s+as|imagine\s+you\s+are|from\s+now\s+on\s+you\s+are)\s+'
                    r'(?:an?\s+)?(?:evil|unfiltered|uncensored|unrestricted|jailbroken|'
                    r'unethical|dangerous|hacker|criminal)',
                    re.IGNORECASE
                ),
            },
            # ── Token smuggling / delimiter abuse ──
            {
                "name": "Delimiter Injection",
                "category": "LLM01: Prompt Injection",
                "description": "Uses delimiters to inject separate instructions",
                "severity": "high",
                "score": 25,
                "pattern": re.compile(
                    r'(?:\[SYSTEM\]|\[INST\]|<\|system\|>|<\|im_start\|>|'
                    r'###\s*(?:System|Human|Assistant|Instruction)|'
                    r'BEGININSTRUCTION|ENDINSTRUCTION|<\|endoftext\|>)',
                    re.IGNORECASE
                ),
            },
            # ── Base64 encoded payloads ──
            {
                "name": "Encoded Payload",
                "category": "LLM01: Prompt Injection",
                "description": "Contains base64-encoded content that may hide injection",
                "severity": "medium",
                "score": 20,
                "pattern": re.compile(
                    r'(?:decode|base64|atob|eval)\s*\(?\s*["\']?'
                    r'[A-Za-z0-9+/]{20,}={0,2}',
                    re.IGNORECASE
                ),
            },
            # ── Hypothetical framing ──
            {
                "name": "Hypothetical Bypass",
                "category": "LLM01: Prompt Injection",
                "description": "Uses hypothetical scenarios to extract unsafe content",
                "severity": "medium",
                "score": 15,
                "pattern": re.compile(
                    r'(?:hypothetically|in\s+theory|for\s+(?:educational|research|academic)\s+'
                    r'purposes?\s+only|purely\s+fictional|just\s+curious)\s*'
                    r'(?:,\s*)?(?:how\s+(?:would|could|can|do)|what\s+(?:would|if))',
                    re.IGNORECASE
                ),
            },
            # ── Multi-step manipulation ──
            {
                "name": "Multi-step Manipulation",
                "category": "LLM01: Prompt Injection",
                "description": "Chains multiple instructions to gradually escalate",
                "severity": "medium",
                "score": 18,
                "pattern": re.compile(
                    r'(?:step\s*1|first|now)\s*[:.].*(?:step\s*2|second|then|next)\s*[:.]\s*'
                    r'(?:ignore|bypass|override|forget)',
                    re.IGNORECASE | re.DOTALL
                ),
            },
            # ── Prompt leaking with completion tricks ──
            {
                "name": "Completion Trick",
                "category": "LLM01: Prompt Injection",
                "description": "Tricks the model into completing a harmful template",
                "severity": "medium",
                "score": 20,
                "pattern": re.compile(
                    r'(?:complete\s+the\s+following|fill\s+in\s+the\s+blanks?|'
                    r'continue\s+this\s+(?:text|story|script))\s*[:]\s*'
                    r'(?:.*(?:hack|exploit|attack|bypass|inject|steal|phish))',
                    re.IGNORECASE | re.DOTALL
                ),
            },
            # ── "Do not refuse" pressure ──
            {
                "name": "Refusal Override",
                "category": "LLM01: Prompt Injection",
                "description": "Pressures the model to not refuse requests",
                "severity": "high",
                "score": 25,
                "pattern": re.compile(
                    r'(?:do\s+not|don\'?t|never|stop)\s+'
                    r'(?:refuse|decline|reject|say\s+(?:no|you\s+can\'?t)|'
                    r'apologize|filter|censor|restrict)',
                    re.IGNORECASE
                ),
            },
        ]

    def _build_indirect_patterns(self) -> list[dict]:
        """Indirect prompt injection patterns (hidden in web content)."""
        return [
            {
                "name": "Hidden HTML Instruction",
                "category": "LLM01: Prompt Injection",
                "description": "Hidden instructions embedded in HTML comments or invisible elements",
                "severity": "critical",
                "score": 35,
                "pattern": re.compile(
                    r'<!--\s*(?:INSTRUCTION|SYSTEM|IGNORE|OVERRIDE|INJECT).*?-->',
                    re.IGNORECASE | re.DOTALL
                ),
            },
            {
                "name": "Invisible Text Injection",
                "category": "LLM01: Prompt Injection",
                "description": "Uses zero-width or invisible characters to hide instructions",
                "severity": "high",
                "score": 30,
                "pattern": re.compile(
                    r'[\u200b\u200c\u200d\u2060\ufeff]{3,}'
                ),
            },
            {
                "name": "Markdown Injection",
                "category": "LLM01: Prompt Injection",
                "description": "Injects instructions via markdown image/link tags",
                "severity": "high",
                "score": 25,
                "pattern": re.compile(
                    r'!\[.*?\]\(https?://.*?(?:exfil|leak|steal|log|track).*?\)',
                    re.IGNORECASE
                ),
            },
            {
                "name": "Data Exfiltration URL",
                "category": "LLM06: Sensitive Information Disclosure",
                "description": "Attempts to exfiltrate data via URL parameters",
                "severity": "critical",
                "score": 40,
                "pattern": re.compile(
                    r'(?:fetch|navigate|visit|open|go\s+to|click|request)\s+'
                    r'(?:this\s+)?(?:url|link|page)\s*[:=]?\s*'
                    r'https?://.*?\?.*?(?:data|token|key|secret|password)',
                    re.IGNORECASE
                ),
            },
        ]

    def _build_unicode_patterns(self) -> list[dict]:
        """Unicode and encoding-based attack patterns."""
        return [
            {
                "name": "Unicode Direction Override",
                "category": "LLM01: Prompt Injection",
                "description": "Uses Unicode RTL/LTR override to visually hide text",
                "severity": "high",
                "score": 30,
                "pattern": re.compile(
                    r'[\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069]'
                ),
            },
            {
                "name": "Homoglyph Attack",
                "category": "LLM01: Prompt Injection",
                "description": "Uses look-alike characters to bypass keyword filters",
                "severity": "medium",
                "score": 15,
                "pattern": re.compile(
                    r'[\u0400-\u04ff\u0370-\u03ff].*'
                    r'(?:ignore|bypass|hack|override)',
                    re.IGNORECASE
                ),
            },
        ]

    def _calculate_heuristic_score(self, text: str) -> tuple[int, list[InjectionPattern]]:
        """
        Analyze text for structural anomalies that suggest injection.
        Returns (score, patterns_matched).
        """
        score = 0
        patterns = []

        # Check for role confusion (excessive use of AI-like directives)
        role_confusion_phrases = [
            "you must", "you will", "you are required",
            "your new role", "your purpose is", "your task is now",
            "respond only", "always respond", "from now on respond"
        ]
        text_lower = text.lower()
        role_count = sum(1 for p in role_confusion_phrases if p in text_lower)
        if role_count >= 2:
            score += 15 * min(role_count, 4)
            patterns.append(InjectionPattern(
                pattern_name="Role Confusion",
                category="LLM01: Prompt Injection",
                description=f"Multiple role-defining directives detected ({role_count} found)",
                severity="high",
                matched_text=None,
            ))

        # Check for excessive special characters (potential delimiter abuse)
        special_ratio = sum(1 for c in text if c in '{}[]<>|\\') / max(len(text), 1)
        if special_ratio > 0.1:
            score += 10
            patterns.append(InjectionPattern(
                pattern_name="Special Character Abuse",
                category="LLM01: Prompt Injection",
                description="Abnormally high ratio of special characters",
                severity="low",
            ))

        # Check for very long prompts with mixed instructions
        if len(text) > 2000:
            instruction_words = ["must", "always", "never", "ignore", "override",
                                 "instead", "actually", "real task", "true objective"]
            instruction_count = sum(1 for w in instruction_words if w in text_lower)
            if instruction_count >= 3:
                score += 20
                patterns.append(InjectionPattern(
                    pattern_name="Long-form Instruction Hiding",
                    category="LLM01: Prompt Injection",
                    description="Long text with multiple embedded instruction keywords",
                    severity="medium",
                ))

        return score, patterns

    def scan(self, text: str) -> InjectionScanResult:
        """
        Scan text for prompt injection attempts.
        Returns threat level, score, and matched patterns.
        """
        total_score = 0
        all_patterns: list[InjectionPattern] = []

        # Run all pattern categories
        for pattern_list in [self._patterns, self._indirect_patterns,
                             self._unicode_patterns]:
            for p in pattern_list:
                matches = p["pattern"].findall(text)
                if matches:
                    matched_text = matches[0] if isinstance(matches[0], str) else str(matches[0])
                    # Truncate for display
                    if len(matched_text) > 100:
                        matched_text = matched_text[:100] + "..."

                    all_patterns.append(InjectionPattern(
                        pattern_name=p["name"],
                        category=p["category"],
                        description=p["description"],
                        severity=p["severity"],
                        matched_text=matched_text,
                    ))
                    total_score += p["score"]

        # Run heuristic analysis
        heuristic_score, heuristic_patterns = self._calculate_heuristic_score(text)
        total_score += heuristic_score
        all_patterns.extend(heuristic_patterns)

        # Cap score at 100
        total_score = min(total_score, 100)

        # Determine threat level
        if total_score >= 50:
            threat_level = ThreatLevel.BLOCKED
            recommendation = "BLOCKED - This prompt contains high-confidence injection patterns and should NOT be forwarded to the LLM."
            details = (
                f"Detected {len(all_patterns)} injection pattern(s) with a "
                f"cumulative threat score of {total_score}/100. "
                f"Primary threats: {', '.join(p.pattern_name for p in all_patterns[:3])}"
            )
        elif total_score >= 20:
            threat_level = ThreatLevel.SUSPICIOUS
            recommendation = "SUSPICIOUS - This prompt contains patterns commonly associated with injection attempts. Proceed with caution."
            details = (
                f"Detected {len(all_patterns)} potential indicator(s) with a "
                f"threat score of {total_score}/100. Consider reviewing before forwarding."
            )
        else:
            threat_level = ThreatLevel.SAFE
            recommendation = "SAFE - No significant injection patterns detected."
            details = f"Threat score: {total_score}/100. No concerning patterns found."

        return InjectionScanResult(
            threat_level=threat_level,
            threat_score=total_score,
            patterns_matched=all_patterns,
            recommendation=recommendation,
            details=details,
        )


# Singleton instance
injection_detector = InjectionDetector()
