import re

def scrub_sensitive_data(text):
    """
    Analyzes and redacts PII. 
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
    blocklist = ["ignore previous instructions", "system prompt", "dan mode", "jailbreak"]
    if any(word.lower() in text.lower() for word in blocklist):
        report["is_threat"] = True
        report["categories"].append("Security Threat")
        report["clean_text"] = "🛡️ SECURITY ALERT: Potential Prompt Injection detected. Request Blocked."
        return report

    # --- 2. CATEGORICAL ANALYSIS (Before Redaction) ---
    
    # Identity Check (Names, Emails, Phones)
    if re.search(r"(?i)(my name is|i am|this is)\s+[A-Z]", text) or \
       re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-.]+', text) or \
       re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text):
        report["categories"].append("Identity")

    # Financial/ID Check (Credit Cards, SSN)
    if re.search(r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}', text) or \
       re.search(r'\d{3}-\d{2}-\d{4}', text):
        report["categories"].append("Financial/ID")

    # Academic Check (10-digit Student IDs)
    if re.search(r'\d{10}', text):
        report["categories"].append("Academic")

    # --- 3. APPLY REDACTION ---
    # Redact Names (introductory phrases)
    text = re.sub(r"(?i)(my name is|i am|this is)\s+([A-Z][a-z]+)", r"\1 [REDACTED NAME]", text)
    # Redact Emails
    text = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-.]+', "[REDACTED EMAIL]", text)
    # Redact Phone Numbers
    text = re.sub(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', "[REDACTED PHONE]", text)
    # Redact Credit Cards
    text = re.sub(r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}', "[REDACTED CARD]", text)
    # Redact SSN
    text = re.sub(r'\d{3}-\d{2}-\d{4}', "[REDACTED SSN]", text)
    # Redact Student ID (10 digits)
    text = re.sub(r'\d{10}', "[REDACTED ID]", text)

    report["clean_text"] = text
    return report