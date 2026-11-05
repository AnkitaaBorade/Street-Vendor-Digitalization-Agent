"""
app.py
------
Core Flask server for the Street Vendor Digitalization Agent.
Handles application routing, API communication, and serves the frontend.
"""

import logging
import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import config
from vendor_agent import VendorProfile, run_scheme_query, run_vendor_agent

# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG if config.FLASK_DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=".", static_url_path="")
app.secret_key = config.SECRET_KEY
CORS(app)


# ---------------------------------------------------------------------------
# Health and config endpoints
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    """Liveness probe."""
    missing = config.validate()
    return jsonify({
        "status": "ok" if not missing else "degraded",
        "missing_config": missing,
        "model": config.GRANITE_MODEL_ID,
        "supported_languages": config.LANGUAGE_LABELS,
    })


@app.route("/api/config", methods=["GET"])
def get_config():
    """Returns non-sensitive runtime configuration for the frontend."""
    return jsonify({
        "supported_languages": config.LANGUAGE_LABELS,
        "granite_model": config.GRANITE_MODEL_ID,
        "rag_max_sources": config.RAG_MAX_SOURCES,
    })


# ---------------------------------------------------------------------------
# Core vendor agent endpoint
# ---------------------------------------------------------------------------

@app.route("/api/generate-profile", methods=["POST"])
def generate_profile():
    """
    POST /api/generate-profile
    Body (JSON): { vendor_input, location, business_type, language }
    Returns: AgentResponse payload as JSON.
    """
    data = request.get_json(force=True, silent=True) or {}

    vendor_input = (data.get("vendor_input") or "").strip()
    location = (data.get("location") or "").strip()
    business_type = (data.get("business_type") or "").strip()
    language = (data.get("language") or "en").strip().lower()

    # Validation
    if not vendor_input:
        return jsonify({"error": "vendor_input is required."}), 400
    if not location:
        return jsonify({"error": "location is required."}), 400
    if not business_type:
        return jsonify({"error": "business_type is required."}), 400
    if language not in config.SUPPORTED_LANGUAGES:
        return jsonify({
            "error": f"Unsupported language '{language}'. Supported: {config.SUPPORTED_LANGUAGES}"
        }), 400

    profile = VendorProfile(
        vendor_input=vendor_input,
        location=location,
        business_type=business_type,
        language=language,
    )

    try:
        result = run_vendor_agent(profile)
    except Exception as exc:
        logger.exception("Vendor agent error: %s", exc)
        return jsonify({"error": f"Agent processing failed: {str(exc)}"}), 500

    return jsonify({
        "generated_text": result.generated_text,
        "sources": result.sources,
        "business_card": result.business_card,
        "scheme_summary": result.scheme_summary,
        "export_text": result.export_text,
        "timestamp": result.timestamp,
    })


# ---------------------------------------------------------------------------
# Scheme eligibility endpoint
# ---------------------------------------------------------------------------

@app.route("/api/scheme-eligibility", methods=["POST"])
def scheme_eligibility():
    """
    POST /api/scheme-eligibility
    Body (JSON): { vendor_details, language }
    Returns: { generated_text, sources }
    """
    data = request.get_json(force=True, silent=True) or {}
    vendor_details = (data.get("vendor_details") or "").strip()
    language = (data.get("language") or "en").strip().lower()

    if not vendor_details:
        return jsonify({"error": "vendor_details is required."}), 400

    try:
        generated_text, sources = run_scheme_query(vendor_details, language)
    except Exception as exc:
        logger.exception("Scheme query error: %s", exc)
        return jsonify({"error": f"Scheme query failed: {str(exc)}"}), 500

    return jsonify({
        "generated_text": generated_text,
        "sources": sources,
    })


# ---------------------------------------------------------------------------
# RAG sources catalogue endpoint
# ---------------------------------------------------------------------------

@app.route("/api/rag-sources", methods=["GET"])
def rag_sources():
    """Returns the full RAG source catalogue for frontend display."""
    from granite_client import RAG_SOURCES
    return jsonify({"sources": RAG_SOURCES})


# ---------------------------------------------------------------------------
# Static frontend serving
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Serve the main frontend page."""
    return send_from_directory(".", "index.html")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    missing = config.validate()
    if missing:
        logger.warning(
            "Missing required configuration keys: %s. "
            "Set them in your .env file before making API calls.",
            missing,
        )
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
