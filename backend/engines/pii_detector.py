"""
PromptShield Gateway - PII Detection Engine
Uses Microsoft Presidio for enterprise-grade PII detection
with custom recognizers for academic environments.
"""
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from models.schemas import PIIEntity, PIIScanResult


# ── Singleton Engines ──────────────────────────────────────────────────

_analyzer = None
_anonymizer = None


def _get_analyzer():
    """Get or create the Presidio Analyzer with custom recognizers."""
    global _analyzer
    if _analyzer is None:
        # Configure NLP engine to use the smaller spaCy model
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        })
        nlp_engine = provider.create_engine()
        _analyzer = AnalyzerEngine(nlp_engine=nlp_engine)

        # Custom: 10-digit Student IDs
        student_id_pattern = Pattern(
            name="student_id_pattern",
            regex=r"\b\d{10}\b",
            score=0.95,
        )
        student_id_recognizer = PatternRecognizer(
            supported_entity="STUDENT_ID",
            patterns=[student_id_pattern],
            name="StudentIdRecognizer",
        )
        _analyzer.registry.add_recognizer(student_id_recognizer)

        # Custom: SSN (XXX-XX-XXXX)
        ssn_pattern = Pattern(
            name="ssn_pattern",
            regex=r"\b\d{3}-\d{2}-\d{4}\b",
            score=0.9,
        )
        ssn_recognizer = PatternRecognizer(
            supported_entity="US_SSN",
            patterns=[ssn_pattern],
            name="CustomSSNRecognizer",
        )
        _analyzer.registry.add_recognizer(ssn_recognizer)

        # Custom: Phone (requires separators to avoid matching student IDs)
        phone_pattern = Pattern(
            name="phone_pattern",
            regex=r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}",
            score=0.85,
        )
        phone_recognizer = PatternRecognizer(
            supported_entity="PHONE_NUMBER",
            patterns=[phone_pattern],
            name="CustomPhoneRecognizer",
        )
        _analyzer.registry.add_recognizer(phone_recognizer)

        # Custom: API Keys (sk-xxx, pk-xxx, etc.)
        api_key_pattern = Pattern(
            name="api_key_pattern",
            regex=r"\b(?:sk|pk|api|key|token|secret|bearer)[_\-]?[A-Za-z0-9_\-]{20,}\b",
            score=0.90,
        )
        api_key_recognizer = PatternRecognizer(
            supported_entity="API_KEY",
            patterns=[api_key_pattern],
            name="ApiKeyRecognizer",
        )
        _analyzer.registry.add_recognizer(api_key_recognizer)

        # Custom: AWS Access Keys
        aws_key_pattern = Pattern(
            name="aws_key_pattern",
            regex=r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
            score=0.95,
        )
        aws_key_recognizer = PatternRecognizer(
            supported_entity="AWS_KEY",
            patterns=[aws_key_pattern],
            name="AwsKeyRecognizer",
        )
        _analyzer.registry.add_recognizer(aws_key_recognizer)

        # Custom: Passwords in text
        password_pattern = Pattern(
            name="password_pattern",
            regex=r"(?:password|passwd|pwd)\s*[:=]\s*\S+",
            score=0.92,
        )
        password_recognizer = PatternRecognizer(
            supported_entity="PASSWORD",
            patterns=[password_pattern],
            name="PasswordRecognizer",
        )
        _analyzer.registry.add_recognizer(password_recognizer)

        # ── Dynamic patterns from settings.json ──
        _load_dynamic_patterns(_analyzer)

    return _analyzer


def _load_dynamic_patterns(analyzer):
    """Load admin-configurable patterns from settings.json."""
    import json
    import os
    settings_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "settings.json",
    )
    if not os.path.exists(settings_path):
        return

    with open(settings_path, "r") as f:
        cfg = json.load(f)

    # Roll Number pattern from admin config
    roll_regex = cfg.get("roll_number_regex")
    if roll_regex:
        roll_pattern = Pattern(
            name="roll_number_pattern",
            regex=roll_regex,
            score=0.95,
        )
        roll_recognizer = PatternRecognizer(
            supported_entity=cfg.get("roll_number_label", "ROLL_NUMBER"),
            patterns=[roll_pattern],
            name="DynamicRollNumberRecognizer",
        )
        analyzer.registry.add_recognizer(roll_recognizer)

        # Register in our maps
        label = cfg.get("roll_number_label", "ROLL_NUMBER")
        ENTITY_CATEGORY_MAP[label] = "Academic"
        OPERATORS[label] = OperatorConfig(
            "replace", {"new_value": f"[REDACTED {label}]"}
        )

    # Additional custom patterns
    for cp in cfg.get("custom_patterns", []):
        try:
            context_list = cp.get("context_required")
            p = Pattern(name=cp["name"], regex=cp["regex"], score=0.85)
            recognizer = PatternRecognizer(
                supported_entity=cp["label"],
                patterns=[p],
                name=f"Dynamic{cp['label']}Recognizer",
                context=context_list,
            )
            analyzer.registry.add_recognizer(recognizer)
            ENTITY_CATEGORY_MAP[cp["label"]] = cp.get("category", "Other")
            OPERATORS[cp["label"]] = OperatorConfig(
                "replace",
                {"new_value": cp.get("redact_tag", f"[REDACTED {cp['label']}]")},
            )
        except Exception:
            pass  # Skip malformed patterns

def _get_anonymizer():
    """Get or create the Presidio Anonymizer."""
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer


# ── Entity to Category Mapping ────────────────────────────────────────

ENTITY_CATEGORY_MAP = {
    # Identity
    "PERSON": "Identity",
    "EMAIL_ADDRESS": "Identity",
    "PHONE_NUMBER": "Identity",
    "URL": "Identity",
    "IP_ADDRESS": "Identity",
    "LOCATION": "Identity",
    "NRP": "Identity",
    # Financial/ID
    "CREDIT_CARD": "Financial/ID",
    "US_SSN": "Financial/ID",
    "US_BANK_NUMBER": "Financial/ID",
    "IBAN_CODE": "Financial/ID",
    "US_PASSPORT": "Financial/ID",
    "US_DRIVER_LICENSE": "Financial/ID",
    "CRYPTO": "Financial/ID",
    "MEDICAL_LICENSE": "Financial/ID",
    # Academic
    "STUDENT_ID": "Academic",
    # Security
    "API_KEY": "Security",
    "AWS_KEY": "Security",
    "PASSWORD": "Security",
    # Skip
    "DATE_TIME": None,
}

# ── Anonymization Operators ───────────────────────────────────────────

OPERATORS = {
    "PERSON": OperatorConfig("replace", {"new_value": "[REDACTED NAME]"}),
    "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[REDACTED EMAIL]"}),
    "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[REDACTED PHONE]"}),
    "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[REDACTED CARD]"}),
    "US_SSN": OperatorConfig("replace", {"new_value": "[REDACTED SSN]"}),
    "STUDENT_ID": OperatorConfig("replace", {"new_value": "[REDACTED STUDENT_ID]"}),
    "URL": OperatorConfig("replace", {"new_value": "[REDACTED URL]"}),
    "IP_ADDRESS": OperatorConfig("replace", {"new_value": "[REDACTED IP]"}),
    "US_BANK_NUMBER": OperatorConfig("replace", {"new_value": "[REDACTED BANK_NUM]"}),
    "IBAN_CODE": OperatorConfig("replace", {"new_value": "[REDACTED IBAN]"}),
    "US_PASSPORT": OperatorConfig("replace", {"new_value": "[REDACTED PASSPORT]"}),
    "US_DRIVER_LICENSE": OperatorConfig("replace", {"new_value": "[REDACTED LICENSE]"}),
    "LOCATION": OperatorConfig("replace", {"new_value": "[REDACTED LOCATION]"}),
    "CRYPTO": OperatorConfig("replace", {"new_value": "[REDACTED CRYPTO]"}),
    "MEDICAL_LICENSE": OperatorConfig("replace", {"new_value": "[REDACTED MEDICAL_ID]"}),
    "NRP": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
    "API_KEY": OperatorConfig("replace", {"new_value": "[REDACTED API_KEY]"}),
    "AWS_KEY": OperatorConfig("replace", {"new_value": "[REDACTED AWS_KEY]"}),
    "PASSWORD": OperatorConfig("replace", {"new_value": "[REDACTED PASSWORD]"}),
    "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
}


class PIIDetector:
    """
    Enterprise-grade PII detection engine powered by Microsoft Presidio.
    Supports 20+ entity types with custom academic recognizers.
    """

    def __init__(self):
        self._analyzer = _get_analyzer()
        self._anonymizer = _get_anonymizer()

    def scan(self, text: str) -> PIIScanResult:
        """
        Scan text for PII entities using Presidio.
        Returns structured results with all detected entities
        and a sanitized version of the text.
        """
        # Analyze with Presidio
        results = self._analyzer.analyze(
            text=text,
            language="en",
            score_threshold=0.5,
        )

        # Filter out ignored entity types (like DATE_TIME)
        results = [
            r for r in results
            if ENTITY_CATEGORY_MAP.get(r.entity_type) is not None
        ]

        # Build entity list
        entities = []
        for r in results:
            redact_tag = OPERATORS.get(
                r.entity_type,
                OPERATORS["DEFAULT"],
            ).params.get("new_value", "[REDACTED]")

            category = ENTITY_CATEGORY_MAP.get(r.entity_type, "Other")

            entities.append(PIIEntity(
                entity_type=r.entity_type,
                original=text[r.start:r.end],
                redacted=redact_tag,
                confidence=round(r.score, 2),
                start=r.start,
                end=r.end,
                category=category,
            ))

        # Sort entities by position
        entities.sort(key=lambda e: e.start)

        # Anonymize text
        if results:
            anonymized = self._anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators=OPERATORS,
            )
            sanitized = anonymized.text
        else:
            sanitized = text

        return PIIScanResult(
            pii_found=len(entities) > 0,
            entity_count=len(entities),
            entities=entities,
            sanitized_text=sanitized,
            original_text=text,
        )


# Singleton instance
pii_detector = PIIDetector()
