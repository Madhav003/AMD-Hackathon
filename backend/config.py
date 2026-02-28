"""
PromptShield Gateway - Configuration
Loads settings from .env file with sensible defaults.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "30/minute")
    LOG_FILE: str = os.getenv("LOG_FILE", "threat_log.json")


settings = Settings()
