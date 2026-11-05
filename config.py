"""
config.py
---------
Centralised configuration handler for the Street Vendor Digitalization Agent.
Loads all environment variables once and exposes them as typed constants.
"""

import os
from dotenv import load_dotenv

# Load .env file at import time
load_dotenv()


class Config:
    # IBM Watson / Granite credentials
    IBM_API_KEY: str = os.getenv("IBM_API_KEY", "4qzPm9aBnd2z-us5weFv4Tl1TcMo57IUMFVK6Tyyw6vA")
    IBM_PROJECT_ID: str = os.getenv("IBM_PROJECT_ID", "6db5aee4-e18c-413a-a036-2a7bec1564b2")
    IBM_WATSONX_URL: str = os.getenv(
        "IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com"
    )

    # Granite model identifiers
    GRANITE_MODEL_ID: str = os.getenv(
        "GRANITE_MODEL_ID", "ibm/granite-3-1-8b-base"
    )
    GRANITE_MAX_TOKENS: int = int(os.getenv("GRANITE_MAX_TOKENS", "1024"))
    GRANITE_TEMPERATURE: float = float(os.getenv("GRANITE_TEMPERATURE", "0.7"))
    GRANITE_TOP_P: float = float(os.getenv("GRANITE_TOP_P", "0.9"))

    # Flask server settings
    FLASK_HOST: str = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")

    # RAG / retrieval settings
    RAG_MAX_SOURCES: int = int(os.getenv("RAG_MAX_SOURCES", "4"))

    # Supported languages
    SUPPORTED_LANGUAGES: list = ["en", "hi", "mr"]
    LANGUAGE_LABELS: dict = {
        "en": "English",
        "hi": "Hindi",
        "mr": "Marathi",
    }

    @classmethod
    def validate(cls) -> list[str]:
        """Return a list of missing required config keys."""
        missing = []
        for key in ("IBM_API_KEY", "IBM_PROJECT_ID"):
            if not getattr(cls, key):
                missing.append(key)
        return missing


# Singleton instance imported by other modules
config = Config()
