from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import re

# --- Initialize Presidio Engines (singleton pattern for performance) ---
_analyzer = None
_anonymizer = None

def _get_analyzer():
    """Get or create the Presidio Analyzer with custom recognizers."""
    global _analyzer
    if _analyzer is None:
        _analyzer = AnalyzerEngine()
        
        # Add custom recognizer for 10-digit Student IDs (high score to prioritize)
        student_id_pattern = Pattern(
            name="student_id_pattern",
            regex=r"\b\d{10}\b",
            score=0.95
        )
        student_id_recognizer = PatternRecognizer(
            supported_entity="STUDENT_ID",
            patterns=[student_id_pattern],
            name="StudentIdRecognizer"
        )
        _analyzer.registry.add_recognizer(student_id_recognizer)
        
        # Add custom recognizer for SSN (XXX-XX-XXXX format)
        ssn_pattern = Pattern(
            name="ssn_pattern",
            regex=r"\b\d{3}-\d{2}-\d{4}\b",
            score=0.9
        )
        ssn_recognizer = PatternRecognizer(
            supported_entity="US_SSN",
            patterns=[ssn_pattern],
            name="CustomSSNRecognizer"
        )
        _analyzer.registry.add_recognizer(ssn_recognizer)
        
        # Add custom recognizer for Phone Numbers (requires separators to avoid matching student IDs)
        phone_pattern = Pattern(
            name="phone_pattern",
            regex=r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}",
            score=0.85
        )
        phone_recognizer = PatternRecognizer(
            supported_entity="PHONE_NUMBER",
            patterns=[phone_pattern],
            name="CustomPhoneRecognizer"
        )
        _analyzer.registry.add_recognizer(phone_recognizer)
        
    return _analyzer

def _get_anonymizer():
    """Get or create the Presidio Anonymizer."""
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer

# --- Entity to Category Mapping ---
ENTITY_CATEGORY_MAP = {
    # Identity
    "PERSON": "Identity",
    "EMAIL_ADDRESS": "Identity",
    "PHONE_NUMBER": "Identity",
    "URL": "Identity",
    "IP_ADDRESS": "Identity",
    
    # Financial/ID
    "CREDIT_CARD": "Financial/ID",
    "US_SSN": "Financial/ID",
    "US_BANK_NUMBER": "Financial/ID",
    "IBAN_CODE": "Financial/ID",
    "US_PASSPORT": "Financial/ID",
    "US_DRIVER_LICENSE": "Financial/ID",
    "CRYPTO": "Financial/ID",
    
    # Academic
    "STUDENT_ID": "Academic",
    "DATE_TIME": None,  # Ignore date/time detections
    
    # Location
    "LOCATION": "Identity",
    "NRP": "Identity",  # Nationality/Religion/Political group
    
    # Medical
    "MEDICAL_LICENSE": "Financial/ID",
}

# --- Anonymization Operators (custom redaction labels) ---
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
    "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
}

def scrub_sensitive_data(text):
    """
    Analyzes and redacts PII using Microsoft Presidio.
    Returns a report with:
    - is_threat: Boolean (True if prompt injection detected)
    - categories: List of categories found (Identity, Financial, Academic, etc.)
    - clean_text: The redacted version of the text
    """
    report = {
        "is_threat": False,
        "categories": [],
        "clean_text": text
    }

    # --- 1. THREAT DETECTION (Prompt Injection) ---
    blocklist = [
        "ignore previous instructions",
        "system prompt",
        "dan mode",
        "jailbreak",
        "ignore all previous",
        "disregard previous",
        "override instructions",
        "pretend you are",
        "act as if you have no restrictions"
    ]
    if any(phrase.lower() in text.lower() for phrase in blocklist):
        report["is_threat"] = True
        report["categories"].append("Security Threat")
        report["clean_text"] = "🛡️ SECURITY ALERT: Potential Prompt Injection detected. Request Blocked."
        return report

    # --- 2. ANALYZE WITH PRESIDIO ---
    analyzer = _get_analyzer()
    anonymizer = _get_anonymizer()
    
    # Analyze text for all supported entities
    results = analyzer.analyze(
        text=text,
        language="en",
        score_threshold=0.5  # Minimum confidence threshold
    )
    
    # --- 3. EXTRACT CATEGORIES ---
    detected_categories = set()
    for result in results:
        entity_type = result.entity_type
        category = ENTITY_CATEGORY_MAP.get(entity_type, "Other")
        if category is not None:  # Skip ignored entity types like DATE_TIME
            detected_categories.add(category)
    
    report["categories"] = list(detected_categories)
    
    # --- 4. ANONYMIZE TEXT ---
    if results:
        anonymized_result = anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=OPERATORS
        )
        report["clean_text"] = anonymized_result.text
    
    return report


def get_detailed_analysis(text):
    """
    Returns detailed analysis of detected entities.
    Useful for debugging or detailed reports.
    """
    analyzer = _get_analyzer()
    results = analyzer.analyze(
        text=text,
        language="en",
        score_threshold=0.5
    )
    
    return [
        {
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": r.score,
            "text": text[r.start:r.end]
        }
        for r in results
    ]