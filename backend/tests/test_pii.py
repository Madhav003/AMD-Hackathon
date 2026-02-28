"""
Tests for the Presidio-based PII Detection Engine.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.pii_detector import pii_detector


class TestEmailDetection:
    def test_basic_email(self):
        result = pii_detector.scan("Contact me at john@example.com")
        assert result.pii_found is True
        assert any(e.entity_type == "EMAIL_ADDRESS" for e in result.entities)

    def test_multiple_emails(self):
        result = pii_detector.scan("Send to alice@uni.edu and bob@company.com")
        assert result.entity_count >= 2

    def test_no_email(self):
        result = pii_detector.scan("No emails here, just a plain sentence.")
        assert not any(e.entity_type == "EMAIL_ADDRESS" for e in result.entities)


class TestSSNDetection:
    def test_ssn_format(self):
        result = pii_detector.scan("My SSN is 321-54-9876")
        assert result.pii_found is True
        assert any(e.entity_type == "US_SSN" for e in result.entities)


class TestCreditCardDetection:
    def test_card_with_spaces(self):
        result = pii_detector.scan("Card: 4111 1111 1111 1111")
        assert result.pii_found is True
        assert any(e.entity_type == "CREDIT_CARD" for e in result.entities)


class TestPhoneDetection:
    def test_us_phone(self):
        result = pii_detector.scan("Call phone 555-867-5309")
        assert result.pii_found is True
        assert any(e.entity_type == "PHONE_NUMBER" for e in result.entities)


class TestIPDetection:
    def test_ipv4(self):
        result = pii_detector.scan("Server is at 192.168.1.42")
        assert result.pii_found is True
        assert any(e.entity_type == "IP_ADDRESS" for e in result.entities)


class TestAPIKeyDetection:
    def test_openai_key(self):
        result = pii_detector.scan("My key is sk-abcdefghijklmnop1234567890")
        assert result.pii_found is True
        assert any(e.entity_type == "API_KEY" for e in result.entities)

    def test_aws_access_key(self):
        result = pii_detector.scan("AWS key: AKIAIOSFODNN7EXAMPLE")
        assert result.pii_found is True
        assert any(e.entity_type == "AWS_KEY" for e in result.entities)


class TestPasswordDetection:
    def test_password_in_text(self):
        result = pii_detector.scan("My password: Sup3rS3cret!")
        assert result.pii_found is True
        assert any(e.entity_type == "PASSWORD" for e in result.entities)


class TestPersonDetection:
    def test_name(self):
        result = pii_detector.scan("My name is John Smith and I live in New York.")
        assert result.pii_found is True
        assert any(e.entity_type == "PERSON" for e in result.entities)


class TestStudentIDDetection:
    def test_student_id(self):
        result = pii_detector.scan("My student ID is 1234567890")
        assert result.pii_found is True
        assert any(e.entity_type == "STUDENT_ID" for e in result.entities)


class TestCategoryMapping:
    def test_identity_category(self):
        result = pii_detector.scan("Contact john@example.com")
        email_entities = [e for e in result.entities if e.entity_type == "EMAIL_ADDRESS"]
        if email_entities:
            assert email_entities[0].category == "Identity"

    def test_financial_category(self):
        result = pii_detector.scan("SSN is 123-45-6789")
        ssn_entities = [e for e in result.entities if e.entity_type == "US_SSN"]
        if ssn_entities:
            assert ssn_entities[0].category == "Financial/ID"


class TestSanitization:
    def test_redaction_labels(self):
        result = pii_detector.scan("Email john@example.com please")
        assert "[REDACTED EMAIL]" in result.sanitized_text

    def test_clean_text_no_pii(self):
        result = pii_detector.scan("What is machine learning?")
        assert result.sanitized_text == "What is machine learning?"
        assert result.pii_found is False
