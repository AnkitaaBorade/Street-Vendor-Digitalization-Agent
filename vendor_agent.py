"""
vendor_agent.py
---------------
Core logic module for the Street Vendor Digitalization Agent.
Orchestrates profile generation, UPI guides, scheme eligibility evaluation,
digital business card creation, and export plan assembly.
"""

import logging
import textwrap
from datetime import datetime

from granite_client import (
    PROFILE_TEMPLATE,
    SCHEME_TEMPLATE,
    generate_with_rag,
    retrieve_relevant_sources,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models (plain dataclasses, no external ORM needed)
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field


@dataclass
class VendorProfile:
    vendor_input: str
    location: str
    business_type: str
    language: str = "en"


@dataclass
class AgentResponse:
    generated_text: str
    sources: list[dict] = field(default_factory=list)
    business_card: dict = field(default_factory=dict)
    scheme_summary: list[dict] = field(default_factory=list)
    export_text: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# ---------------------------------------------------------------------------
# Scheme eligibility matrix
# ---------------------------------------------------------------------------

SCHEMES = [
    {
        "id": "pm_svanidhi",
        "name": "PM SVANidhi Micro-Loan",
        "amounts": "Rs 10,000 / Rs 20,000 / Rs 50,000",
        "portal": "https://pmsvanidhi.mohua.gov.in",
        "eligible_types": [
            "street vendor", "hawker", "fruit", "vegetable", "food", "tea",
            "snacks", "flower", "newspaper", "cobbler", "tailor", "barber",
            "laundry", "pan", "stationary", "toy", "clothes", "fish",
        ],
        "documents": [
            "Aadhaar Card",
            "Vendor Certificate / Town Vending Committee Letter",
            "Bank Account details",
            "Mobile number linked to Aadhaar",
        ],
        "notes": "Exclusively for urban street vendors. Certificate of Vending required.",
    },
    {
        "id": "udyam_assist",
        "name": "Udyam Assist Platform",
        "amounts": "Registration (Free)",
        "portal": "https://udyamassist.gov.in",
        "eligible_types": [
            "any", "micro", "small", "vendor", "artisan", "trader", "shop",
        ],
        "documents": [
            "Aadhaar Card",
            "Mobile number linked to Aadhaar",
            "Self-declaration of business activity",
        ],
        "notes": "No GST or ITR required. Opens access to bank credit and MSME benefits.",
    },
    {
        "id": "mudra_shishu",
        "name": "MUDRA Shishu Loan",
        "amounts": "Up to Rs 50,000",
        "portal": "https://www.mudra.org.in",
        "eligible_types": [
            "any", "micro", "vendor", "shop", "food", "service", "manufacturing",
        ],
        "documents": [
            "Aadhaar Card",
            "PAN Card (or Form 60)",
            "Bank Statement (6 months)",
            "Proof of Business Address",
            "Passport-size photograph",
        ],
        "notes": "Apply through any public sector bank, MFI, or NBFC. No collateral required.",
    },
    {
        "id": "pm_vishwakarma",
        "name": "PM Vishwakarma Scheme",
        "amounts": "Rs 15,000 toolkit + Rs 1 lakh / Rs 2 lakh credit",
        "portal": "https://pmvishwakarma.gov.in",
        "eligible_types": [
            "carpenter", "blacksmith", "goldsmith", "potter", "cobbler", "tailor",
            "weaver", "barber", "washerman", "doll", "toy", "basket", "broom",
            "fishing net", "mason", "sculptor", "armourer", "locksmith",
        ],
        "documents": [
            "Aadhaar Card",
            "Proof of traditional craft/trade",
            "Mobile number linked to Aadhaar",
            "Bank Account details",
        ],
        "notes": "Targeted at 18 traditional artisan and craftsperson categories.",
    },
]


def evaluate_scheme_eligibility(vendor_input: str, business_type: str) -> list[dict]:
    """
    Rule-based pre-screening of government schemes based on vendor description.
    Returns a list of scheme objects with an `eligible` boolean and `reason`.
    """
    combined = f"{vendor_input} {business_type}".lower()
    results = []

    for scheme in SCHEMES:
        eligible = False
        reason = "Business type does not match this scheme's target group."

        for keyword in scheme["eligible_types"]:
            if keyword == "any" or keyword in combined:
                eligible = True
                reason = f"Your business activity matches the '{keyword}' category under this scheme."
                break

        results.append({
            "scheme_id": scheme["id"],
            "scheme_name": scheme["name"],
            "amounts": scheme["amounts"],
            "portal": scheme["portal"],
            "eligible": eligible,
            "reason": reason,
            "documents": scheme["documents"],
            "notes": scheme["notes"],
        })

    return results


# ---------------------------------------------------------------------------
# Digital Business Card generator
# ---------------------------------------------------------------------------

def generate_business_card(vendor_input: str, location: str, business_type: str) -> dict:
    """
    Assembles a structured Digital Business Card payload.
    The frontend renders this as a card with a QR placeholder.
    """
    # Derive a clean business name from the input
    words = vendor_input.strip().split()
    name_candidate = " ".join(w.capitalize() for w in words[:4])

    # Category tag
    category_map = {
        "fruit": "Fresh Produce",
        "vegetable": "Fresh Produce",
        "food": "Food and Beverages",
        "tea": "Food and Beverages",
        "snacks": "Food and Beverages",
        "tailor": "Apparel and Alterations",
        "clothes": "Retail Clothing",
        "cobbler": "Footwear Repair",
        "barber": "Personal Care Services",
        "flower": "Floral Products",
        "fish": "Seafood and Non-Veg",
        "toy": "Toys and Novelties",
        "stationery": "Stationery and Books",
    }
    category = "Micro Retail Business"
    for key, val in category_map.items():
        if key in vendor_input.lower() or key in business_type.lower():
            category = val
            break

    return {
        "business_name": name_candidate,
        "category": category,
        "location": location,
        "tagline": f"Your trusted local {business_type.lower()} in {location}.",
        "upi_placeholder": "vendor@upi",
        "qr_placeholder": True,
        "listing_links": [
            {"platform": "Google Business Profile", "url": "https://business.google.com"},
            {"platform": "ONDC Network", "url": "https://ondc.org"},
            {"platform": "JustDial", "url": "https://www.justdial.com"},
        ],
    }


# ---------------------------------------------------------------------------
# Export plan assembler
# ---------------------------------------------------------------------------

def assemble_export_plan(
    vendor_profile: VendorProfile,
    generated_text: str,
    scheme_summary: list[dict],
    business_card: dict,
    sources: list[dict],
) -> str:
    """
    Assembles a plain-text export plan suitable for offline access or printing.
    """
    lines = [
        "=" * 70,
        "STREET VENDOR DIGITAL PLAN",
        f"Generated: {datetime.utcnow().strftime('%d %B %Y, %H:%M UTC')}",
        "=" * 70,
        "",
        "VENDOR DETAILS",
        "-" * 40,
        f"Input     : {vendor_profile.vendor_input}",
        f"Location  : {vendor_profile.location}",
        f"Business  : {vendor_profile.business_type}",
        f"Language  : {vendor_profile.language.upper()}",
        "",
        "DIGITAL BUSINESS CARD",
        "-" * 40,
        f"Business Name : {business_card.get('business_name', 'N/A')}",
        f"Category      : {business_card.get('category', 'N/A')}",
        f"Tagline       : {business_card.get('tagline', 'N/A')}",
        f"UPI Handle    : {business_card.get('upi_placeholder', 'N/A')}",
        "",
        "AI-GENERATED DIGITAL PLAN",
        "-" * 40,
        "",
    ]

    # Wrap long lines for readability in plain text
    for para in generated_text.split("\n"):
        wrapped = textwrap.fill(para, width=70) if len(para) > 70 else para
        lines.append(wrapped)

    lines += [
        "",
        "SCHEME ELIGIBILITY SUMMARY",
        "-" * 40,
    ]
    for s in scheme_summary:
        status = "ELIGIBLE" if s["eligible"] else "NOT ELIGIBLE"
        lines.append(f"  {s['scheme_name']}: {status}")
        lines.append(f"    Amount   : {s['amounts']}")
        lines.append(f"    Portal   : {s['portal']}")
        lines.append(f"    Note     : {s['notes']}")
        lines.append("")

    lines += [
        "RETRIEVED SOURCES",
        "-" * 40,
    ]
    for src in sources:
        lines.append(f"  - {src['name']}: {src['url']}")

    lines += [
        "",
        "=" * 70,
        "This plan was generated by the Street Vendor Digitalization Agent",
        "powered by IBM Granite AI and RAG integration.",
        "=" * 70,
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main orchestration function
# ---------------------------------------------------------------------------

def run_vendor_agent(vendor_profile: VendorProfile) -> AgentResponse:
    """
    Primary entry point. Accepts a VendorProfile, runs the full pipeline,
    and returns a populated AgentResponse.
    """
    logger.info(
        "Running vendor agent for: %s | %s | %s",
        vendor_profile.vendor_input,
        vendor_profile.location,
        vendor_profile.business_type,
    )

    # Step 1: Generate AI profile via Granite + RAG
    generated_text, sources = generate_with_rag(
        user_query=f"{vendor_profile.vendor_input} {vendor_profile.location} {vendor_profile.business_type}",
        template=PROFILE_TEMPLATE,
        template_vars={
            "vendor_input": vendor_profile.vendor_input,
            "location": vendor_profile.location,
            "business_type": vendor_profile.business_type,
        },
        language=vendor_profile.language,
    )

    # Step 2: Evaluate scheme eligibility (rule-based pre-screen)
    scheme_summary = evaluate_scheme_eligibility(
        vendor_profile.vendor_input, vendor_profile.business_type
    )

    # Step 3: Generate digital business card payload
    business_card = generate_business_card(
        vendor_profile.vendor_input,
        vendor_profile.location,
        vendor_profile.business_type,
    )

    # Step 4: Assemble exportable plain-text plan
    export_text = assemble_export_plan(
        vendor_profile, generated_text, scheme_summary, business_card, sources
    )

    return AgentResponse(
        generated_text=generated_text,
        sources=sources,
        business_card=business_card,
        scheme_summary=scheme_summary,
        export_text=export_text,
    )


def run_scheme_query(vendor_details: str, language: str = "en") -> tuple[str, list[dict]]:
    """
    Dedicated scheme eligibility deep-dive using Granite.
    Returns (generated_text, sources).
    """
    logger.info("Running scheme query for: %s", vendor_details)
    return generate_with_rag(
        user_query=vendor_details,
        template=SCHEME_TEMPLATE,
        template_vars={"vendor_details": vendor_details},
        language=language,
    )
