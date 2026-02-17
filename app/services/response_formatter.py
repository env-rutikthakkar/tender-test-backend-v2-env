"""
Response Formatter
Restructures API response to remove duplicates and make sections concise for better UX
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def format_tender_response(tender_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format tender response to:
    1. Keep eligibility_snapshot with all separate fields
    2. Populate vendor_decision_hint.eligible_if with eligibility summary
    3. Move pre_qualification_requirement to metadata (remove duplicate)
    """
    formatted = tender_data.copy()

    # 1. Keep eligibility_snapshot as-is (all separate fields visible)
    eligibility_snapshot = formatted.get("eligibility_snapshot", {})

    # 2. Populate eligible_if in vendor_decision_hint with eligibility summary
    if eligibility_snapshot:
        eligibility_summary = _create_eligibility_summary(eligibility_snapshot)
        if "vendor_decision_hint" not in formatted:
            formatted["vendor_decision_hint"] = {}
        formatted["vendor_decision_hint"]["eligible_if"] = eligibility_summary

    # 3. Move pre_qualification_requirement to metadata (avoid duplication in main response)
    pre_qual = formatted.pop("pre_qualification_requirement", None)
    if "_metadata" not in formatted:
        formatted["_metadata"] = {}
    if pre_qual:
        formatted["_metadata"]["pre_qualification_requirement"] = pre_qual

    return formatted


def _create_eligibility_summary(eligibility_snapshot: Dict[str, Any]) -> str:
    """
    Create a brief eligibility summary from detailed snapshot.
    Example:
    "Minimum ₹4 Lakh turnover with 3 years experience. MSME/Startup eligible with full relaxation.
    Consortium allowed. Digital certificate required."
    """
    summary_parts = []

    # Turnover
    turnover = eligibility_snapshot.get("turnover_requirement", "")
    if turnover:
        summary_parts.append(f"Minimum {turnover} turnover")

    # Experience
    experience = eligibility_snapshot.get("experience_required", "")
    if experience:
        summary_parts.append(f"with {experience.lower()} experience")

    # OEM Turnover (GeM)
    oem_turnover = eligibility_snapshot.get("oem_turnover_requirement", "")
    if oem_turnover:
        summary_parts.append(f"OEM {oem_turnover} turnover")

    # MSME/Startup
    msme = eligibility_snapshot.get("mse_relaxation", "")
    startup = eligibility_snapshot.get("startup_relaxation", "")
    exemptions = []
    if msme and "yes" in msme.lower():
        exemptions.append("MSME")
    if startup and "yes" in startup.lower():
        exemptions.append("Startup")

    if exemptions:
        summary_parts.append(f"{'/'.join(exemptions)} eligible with relaxation")

    # Consortium/JV
    consortium = eligibility_snapshot.get("consortium_or_jv_allowed", "")
    if consortium and "yes" in consortium.lower():
        summary_parts.append("Consortium/JV allowed")

    # Infrastructure
    infrastructure = eligibility_snapshot.get("bidder_technical_infrastructure", "")
    if infrastructure:
        summary_parts.append("Digital certificate required")

    # International
    intl = eligibility_snapshot.get("international_bidders_allowed", "")
    if intl and "yes" in intl.lower():
        summary_parts.append("International bidders welcome")

    return ". ".join(summary_parts) + "."


def _extract_key_requirements(eligibility_snapshot: Dict[str, Any]) -> str:
    """Extract only the most important eligibility requirements as formatted string."""
    key_reqs = []

    fields_to_include = [
        "who_can_bid",
        "turnover_requirement",
        "experience_required",
        "oem_turnover_requirement",
        "consortium_or_jv_allowed",
        "mse_relaxation",
        "startup_relaxation",
        "bidder_technical_infrastructure",
    ]

    for field in fields_to_include:
        if field in eligibility_snapshot:
            value = eligibility_snapshot[field]
            if value and str(value).strip() and str(value).lower() not in ["not found", "not mentioned", "n/a"]:
                # Format field name for display
                display_name = field.replace("_", " ").title()
                key_reqs.append(f"{display_name}: {value}")

    return " | ".join(key_reqs) if key_reqs else ""


def format_gem_response(tender_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format response specifically for GeM tenders."""
    # Use standard formatting - no GeM-specific section
    # All fields kept in their original sections
    return format_tender_response(tender_data)


def format_cppp_response(tender_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format response specifically for CPPP tenders."""
    # Use standard formatting - no CPPP-specific section
    # All fields kept in their original sections
    return format_tender_response(tender_data)


def format_response_by_portal(tender_data: Dict[str, Any], portal_type: str) -> Dict[str, Any]:
    """Route to portal-specific formatting."""
    logger.info(f"Formatting response for {portal_type} portal")

    if portal_type == "GeM":
        return format_gem_response(tender_data)
    elif portal_type == "CPPP":
        return format_cppp_response(tender_data)
    else:
        return format_tender_response(tender_data)
