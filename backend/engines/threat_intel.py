"""
PromptShield Gateway — Threat Intelligence Module
Maintains a database of known injection signatures categorized by
OWASP Top 10 for LLMs. Provides human-readable explanations.
"""
import json
import os

_SIGNATURES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "storage", "known_signatures.json"
)


class ThreatIntel:
    """Threat intelligence lookup and categorization engine."""

    OWASP_LLM_TOP_10 = {
        "LLM01": {
            "name": "Prompt Injection",
            "description": "Manipulating LLMs via crafted inputs to cause unintended actions",
            "impact": "Unauthorized access, data exposure, social engineering",
        },
        "LLM02": {
            "name": "Insecure Output Handling",
            "description": "Insufficient validation of LLM outputs before passing to other components",
            "impact": "XSS, CSRF, SSRF, privilege escalation, remote code execution",
        },
        "LLM03": {
            "name": "Training Data Poisoning",
            "description": "Tampered training data introducing vulnerabilities or biases",
            "impact": "Model corruption, biased outputs, security vulnerabilities",
        },
        "LLM04": {
            "name": "Model Denial of Service",
            "description": "Causing resource-heavy operations on LLMs leading to service degradation",
            "impact": "Service unavailability, increased costs",
        },
        "LLM05": {
            "name": "Supply Chain Vulnerabilities",
            "description": "Compromised components in the LLM supply chain",
            "impact": "Model compromise, data breaches",
        },
        "LLM06": {
            "name": "Sensitive Information Disclosure",
            "description": "LLMs inadvertently revealing sensitive data in responses",
            "impact": "Exposure of PII, IP, credentials, proprietary data",
        },
        "LLM07": {
            "name": "Insecure Plugin Design",
            "description": "LLM plugins with insufficient access control",
            "impact": "Data leakage, remote code execution, privilege escalation",
        },
        "LLM08": {
            "name": "Excessive Agency",
            "description": "Granting LLMs too much autonomy to take actions",
            "impact": "Unintended actions, system compromise",
        },
        "LLM09": {
            "name": "Overreliance",
            "description": "Uncritical reliance on LLM-generated content",
            "impact": "Misinformation, security vulnerabilities, legal liabilities",
        },
        "LLM10": {
            "name": "Model Theft",
            "description": "Unauthorized access to proprietary LLM models",
            "impact": "Economic loss, competitive disadvantage, access to sensitive info",
        },
    }

    def __init__(self):
        self.signatures = self._load_signatures()

    def _load_signatures(self) -> list[dict]:
        """Load known injection signatures from JSON database."""
        try:
            with open(_SIGNATURES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def get_owasp_info(self, category_id: str) -> dict:
        """Get OWASP LLM Top 10 info for a category."""
        code = category_id.split(":")[0].strip() if ":" in category_id else category_id
        return self.OWASP_LLM_TOP_10.get(code, {
            "name": "Unknown",
            "description": "Category not found",
            "impact": "Unknown",
        })

    def explain_threat(self, pattern_name: str, category: str) -> str:
        """Generate a human-readable explanation for a detected threat."""
        owasp = self.get_owasp_info(category)

        # Check if we have a specific signature for this
        for sig in self.signatures:
            if sig.get("name") == pattern_name:
                return (
                    f"[THREAT] **{pattern_name}**\n"
                    f"Category: {category} — {owasp['name']}\n"
                    f"What it does: {sig.get('explanation', owasp['description'])}\n"
                    f"Risk: {sig.get('risk', owasp['impact'])}\n"
                    f"Mitigation: {sig.get('mitigation', 'Block and log the request')}"
                )

        return (
            f"[THREAT] **{pattern_name}**\n"
            f"Category: {category} — {owasp['name']}\n"
            f"What it does: {owasp['description']}\n"
            f"Risk: {owasp['impact']}\n"
            f"Mitigation: Block and log the request"
        )

    def get_all_categories(self) -> dict:
        """Return all OWASP LLM Top 10 categories."""
        return self.OWASP_LLM_TOP_10


# Singleton
threat_intel = ThreatIntel()
