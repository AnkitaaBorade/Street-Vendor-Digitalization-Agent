"""
granite_client.py
-----------------
Dedicated module for IBM Granite API requests and RAG integration.
Handles authentication, token management, prompt construction, and
retrieval-augmented generation calls to IBM watsonx.ai.
"""

import logging
import time
from typing import Optional

import requests

from config import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# IBM IAM token management
# ---------------------------------------------------------------------------

_iam_token: Optional[str] = None
_iam_token_expiry: float = 0.0
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
IAM_TOKEN_BUFFER_SECS = 60  # refresh this many seconds before actual expiry


def _get_iam_token() -> str:
    """Return a valid IBM IAM bearer token, refreshing if necessary."""
    global _iam_token, _iam_token_expiry

    if _iam_token and time.time() < _iam_token_expiry:
        return _iam_token

    payload = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": config.IBM_API_KEY,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(IAM_TOKEN_URL, data=payload, headers=headers, timeout=15)
    response.raise_for_status()

    data = response.json()
    _iam_token = data["access_token"]
    _iam_token_expiry = time.time() + data.get("expires_in", 3600) - IAM_TOKEN_BUFFER_SECS
    logger.debug("IBM IAM token refreshed successfully.")
    return _iam_token


# ---------------------------------------------------------------------------
# RAG source catalogue
# ---------------------------------------------------------------------------

RAG_SOURCES = [
    {
        "id": "pm_svanidhi",
        "name": "PM SVANidhi Portal",
        "url": "https://pmsvanidhi.mohua.gov.in",
        "description": "Working capital micro-loans (Rs 10,000 / 20,000 / 50,000) for street vendors.",
        "tags": ["loan", "credit", "street vendor", "working capital"],
    },
    {
        "id": "msme_ministry",
        "name": "Ministry of MSME",
        "url": "https://msme.gov.in",
        "description": "MSME schemes, Udyam registration, policy circulars, and enterprise support.",
        "tags": ["msme", "registration", "udyam", "enterprise", "policy"],
    },
    {
        "id": "mudra_loans",
        "name": "MUDRA Shishu Loans",
        "url": "https://www.mudra.org.in",
        "description": "Pradhan Mantri MUDRA Yojana - Shishu category loans up to Rs 50,000.",
        "tags": ["mudra", "loan", "micro", "shishu"],
    },
    {
        "id": "pm_vishwakarma",
        "name": "PM Vishwakarma Scheme",
        "url": "https://pmvishwakarma.gov.in",
        "description": "Skill training, toolkit support, and credit linkage for artisans and craftspeople.",
        "tags": ["vishwakarma", "artisan", "craft", "skill", "training"],
    },
    {
        "id": "upi_merchant",
        "name": "UPI Merchant Onboarding (NPCI)",
        "url": "https://www.npci.org.in/what-we-do/upi/product-overview",
        "description": "Official NPCI guide for merchant UPI QR code setup and onboarding.",
        "tags": ["upi", "qr", "payment", "merchant", "npci"],
    },
    {
        "id": "udyam_assist",
        "name": "Udyam Assist Platform",
        "url": "https://udyamassist.gov.in",
        "description": "Simplified informal enterprise registration for micro-businesses without GST/ITR.",
        "tags": ["udyam", "registration", "informal", "micro"],
    },
    {
        "id": "google_business",
        "name": "Google Business Profile",
        "url": "https://business.google.com",
        "description": "Free local SEO listing for hyperlocal discoverability on Google Maps.",
        "tags": ["seo", "listing", "google", "maps", "local", "digital"],
    },
    {
        "id": "ondc",
        "name": "ONDC Network",
        "url": "https://ondc.org",
        "description": "Open Network for Digital Commerce - onboard as a seller on India's open e-commerce network.",
        "tags": ["ondc", "ecommerce", "digital", "seller", "listing"],
    },
]


def retrieve_relevant_sources(query: str, max_results: int = None) -> list[dict]:
    """
    Lightweight keyword-based retrieval over the static RAG source catalogue.
    Returns the most relevant sources for the given vendor query.
    """
    max_results = max_results or config.RAG_MAX_SOURCES
    query_lower = query.lower()
    scored: list[tuple[int, dict]] = []

    for source in RAG_SOURCES:
        score = 0
        for tag in source["tags"]:
            if tag in query_lower:
                score += 2
        for word in query_lower.split():
            if word in source["description"].lower():
                score += 1
        scored.append((score, source))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for _, s in scored[:max_results] if _ >= 0]
    # Always include at least the top max_results even with zero score
    return top[:max_results]


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a Street Vendor Digitalization Agent for India. "
    "Your role is to help local hawkers, micro-entrepreneurs, and informal street vendors "
    "become digitally visible and financially included. "
    "You provide actionable, specific, and practical guidance on: "
    "digital business profiles, UPI payment setup, QR codes, government scheme eligibility, "
    "local SEO, online listing platforms (Google Maps, ONDC, Meesho), "
    "MSME registration, micro-credit schemes, and customer engagement. "
    "Always be concise, structured with clear headings, and avoid vague generalities. "
    "Do not use emojis. Use professional language. "
    "When applicable, cite the specific government scheme or platform by name."
)

LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in clear, simple English.",
    "hi": "Respond in Hindi (Devanagari script). Use simple, conversational Hindi that a street vendor can understand.",
    "mr": "Respond in Marathi (Devanagari script). Use simple, conversational Marathi that a street vendor can understand.",
}

PROFILE_TEMPLATE = """
Generate a structured Digital Business Profile for the following vendor.

Vendor Input: {vendor_input}
Location: {location}
Business Type: {business_type}

Include the following sections with clear headings:
1. Business Profile Summary (name suggestion, tagline, category)
2. UPI Payment Setup Steps (step-by-step for BHIM/PhonePe/Google Pay)
3. Online Listing Recommendations (Google Business Profile, ONDC, local directories)
4. Local SEO Tips (3-5 actionable tips for the specific locality)
5. Government Scheme Eligibility (check against PM SVANidhi, Udyam Assist, MUDRA, PM Vishwakarma)
6. Customer Engagement Strategy (WhatsApp Business, loyalty tips, peak hour marketing)
7. Promotional Material Suggestions (banner text, visiting card content)

Retrieved Policy Context:
{rag_context}

{language_instruction}
"""

SCHEME_TEMPLATE = """
Evaluate government scheme eligibility for the following vendor profile.

Vendor Details: {vendor_details}

Assess eligibility and provide specific action steps for each of the following schemes:
1. PM SVANidhi Micro-Loan (Rs 10,000 initial / Rs 20,000 / Rs 50,000 enhanced)
2. Udyam Assist Platform Registration
3. MUDRA Shishu Loan (up to Rs 50,000)
4. PM Vishwakarma Scheme (if applicable craft/skill category)

For each scheme, state: Eligibility Status | Key Documents Required | Nearest Application Method

Retrieved Policy Context:
{rag_context}

{language_instruction}
"""


# ---------------------------------------------------------------------------
# Core Granite API call
# ---------------------------------------------------------------------------

def call_granite(prompt: str, max_tokens: int = None, temperature: float = None) -> str:
    """
    Send a prompt to IBM Granite via watsonx.ai and return the generated text.
    Raises requests.HTTPError on API failures.
    """
    token = _get_iam_token()
    url = f"{config.IBM_WATSONX_URL}/ml/v1/text/generation?version=2024-03-19"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    body = {
        "model_id": config.GRANITE_MODEL_ID,
        "project_id": config.IBM_PROJECT_ID,
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": max_tokens or config.GRANITE_MAX_TOKENS,
            "repetition_penalty": 1.1,
        },
    }

    logger.debug("Calling IBM Granite model: %s", config.GRANITE_MODEL_ID)
    response = requests.post(url, json=body, headers=headers, timeout=60)
    response.raise_for_status()

    data = response.json()
    results = data.get("results", [])
    if not results:
        raise ValueError("Empty results returned from Granite API.")

    generated_text = results[0].get("generated_text", "").strip()
    logger.debug("Granite response received (%d chars).", len(generated_text))
    return generated_text


def generate_with_rag(
    user_query: str,
    template: str,
    template_vars: dict,
    language: str = "en",
) -> tuple[str, list[dict]]:
    """
    High-level RAG generation function.
    Retrieves relevant sources, builds the prompt, calls Granite,
    and returns (generated_text, sources_used).
    """
    sources = retrieve_relevant_sources(user_query)
    rag_context = "\n".join(
        f"- {s['name']} ({s['url']}): {s['description']}" for s in sources
    )
    language_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])

    prompt_vars = {
        **template_vars,
        "rag_context": rag_context,
        "language_instruction": language_instruction,
    }

    full_prompt = f"{SYSTEM_PROMPT}\n\n{template.format(**prompt_vars)}"
    generated_text = call_granite(full_prompt)
    return generated_text, sources
