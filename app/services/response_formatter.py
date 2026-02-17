"""
Response Formatter Service
Restructures and cleans the extracted tender data for optimal API presentation.
Handles eligibility summarization and portal-specific metadata movement.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def format_tender_response(tender_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply common formatting logic to any tender response.
    1. Generates an eligibility summary for vendor decision hints.
    2. Moves raw pre-qualification text to metadata to avoid clutter.

    Args:
        tender_data (Dict[str, Any]): The raw structured tender analysis.

    Returns:
        Dict[str, Any]: The formatted response.
    """
    formatted = tender_data.copy()

    # Generate eligibility summary for decision hint
    eligibility_snapshot = formatted.get("eligibility_snapshot", {})
    if eligibility_snapshot:
        summary = _create_eligibility_summary(eligibility_snapshot)
        if "vendor_decision_hint" not in formatted:
            formatted["vendor_decision_hint"] = {}
        formatted["vendor_decision_hint"]["eligible_if"] = summary

    # Move raw pre-qualification requirement to metadata to avoid duplication in main payload
    pre_qual = formatted.pop("pre_qualification_requirement", None)
    if "_metadata" not in formatted:
        formatted["_metadata"] = {}
    if pre_qual:
        formatted["_metadata"]["pre_qualification_requirement"] = pre_qual

    return formatted

def _create_eligibility_summary(snapshot: Dict[str, Any]) -> str:
    """
    Construct a human-readable sentence summarizing the eligibility requirements.

    Args:
        snapshot (Dict[str, Any]): The eligibility snapshot section.

    Returns:
        str: A concatenated summary string.
    """
    parts = []

    # Financials
    turnover = snapshot.get("turnover_requirement")
    if turnover:
        parts.append(f"Minimum {turnover} turnover")

    experience = snapshot.get("experience_required")
    if experience:
        parts.append(f"with {experience.lower()} experience")

    oem_turnover = snapshot.get("oem_turnover_requirement")
    if oem_turnover:
        parts.append(f"OEM {oem_turnover} turnover")

    # Relaxations
    exemptions = []
    if "yes" in str(snapshot.get("mse_relaxation", "")).lower():
        exemptions.append("MSME")
    if "yes" in str(snapshot.get("startup_relaxation", "")).lower():
        exemptions.append("Startup")
    if exemptions:
        parts.append(f"{'/'.join(exemptions)} eligible with relaxation")

    # Legal/Misc
    if "yes" in str(snapshot.get("consortium_or_jv_allowed", "")).lower():
        parts.append("Consortium/JV allowed")

    if snapshot.get("bidder_technical_infrastructure"):
        parts.append("Digital certificate and specific infrastructure required")

    return ". ".join(parts) + "." if parts else "Refer to detailed eligibility section."

def format_response_by_portal(tender_data: Dict[str, Any], portal_type: str) -> Dict[str, Any]:
    """
    Entry point for portal-specific response formatting.
    Currently maps all portals to a unified standard format but allows for future divergence.

    Args:
        tender_data (Dict[str, Any]): Raw data.
        portal_type (str): GeM, CPPP, or Generic.

    Returns:
        Dict[str, Any]: Formatted data.
    """
    logger.info(f"Formatting response for {portal_type} portal")
    # All portals currently use the standard transformation
    return format_tender_response(tender_data)
