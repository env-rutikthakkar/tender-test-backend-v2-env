"""
Portal-Specific Validation Service
Validates extraction completeness based on portal requirements (GeM, CPPP, Generic).
Provides warnings and errors for missing critical fields.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# GeM-required fields configuration
GEM_REQUIRED_FIELDS = {
    "tender_meta": ["tender_id", "tender_title", "portal", "item_category", "total_quantity", "boq_title"],
    "eligibility_snapshot": ["turnover_requirement", "oem_turnover_requirement", "experience_required"],
    "financial_requirements": ["epbg_details"],
    "additional_important_information": ["evaluation_method", "bid_to_ra_enabled", "technical_clarification_time", "buyer_added_atc"],
    "root": ["pre_qualification_requirement"]
}

# CPPP-required fields configuration
CPPP_REQUIRED_FIELDS = {
    "tender_meta": ["tender_id", "tender_title", "portal"],
    "key_dates": ["date_and_time_of_issue", "due_date_and_time_of_submission"],
    "documents_required": ["online_submission_documents", "offline_submission_documents"],
    "eligibility_snapshot": ["bidder_technical_infrastructure"],
}

EMPTY_INDICATORS = ["not found", "not mentioned", "not specified", "n/a", "", None]

def is_field_empty(value: Any) -> bool:
    """
    Check if a field value is considered empty based on predefined indicators.

    Args:
        value (Any): Value to check.

    Returns:
        bool: True if empty, False otherwise.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return value.lower().strip() in EMPTY_INDICATORS
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False

def validate_gem_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate GeM-specific fields are present and populated."""
    result = {"is_valid": True, "missing_fields": [], "warnings": []}

    for section, fields in GEM_REQUIRED_FIELDS.items():
        section_data = data if section == "root" else data.get(section, {})
        # Ensure section_data is a dict before calling .get()
        if not isinstance(section_data, dict):
            logger.warning(f"Validation: Section {section} is not a dict: {type(section_data)}")
            section_data = {}

        for field in fields:
            if is_field_empty(section_data.get(field)):
                result["missing_fields"].append(f"{section}.{field}")
                result["is_valid"] = False

    # GeM-specific warnings
    if is_field_empty(data.get("pre_qualification_requirement")):
        result["warnings"].append("pre_qualification_requirement is empty - GeM tenders MUST have this")

    # Access documents_required as it is a top-level list in the current schema
    docs = data.get("documents_required", [])
    if not docs:
        result["warnings"].append("documents_required is empty - should contain pre-qual documents")

    return result

def validate_cppp_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate CPPP-specific fields are present and populated."""
    result = {"is_valid": True, "missing_fields": [], "warnings": []}

    for section, fields in CPPP_REQUIRED_FIELDS.items():
        section_data = data if section == "root" else data.get(section, {})
        if not isinstance(section_data, dict):
            section_data = {}

        for field in fields:
            if is_field_empty(section_data.get(field)):
                result["missing_fields"].append(f"{section}.{field}")
                result["is_valid"] = False

    # Check top-level lists for CPPP
    if not data.get("online_submission_documents"):
        result["warnings"].append("online_submission_documents is empty - CPPP tenders must separate online docs")
    if not data.get("offline_submission_documents"):
        result["warnings"].append("offline_submission_documents is empty - check if physical submission is required")

    return result

def validate_generic_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate common fields for generic portals.

    Args:
        data (Dict[str, Any]): Extracted tender data.

    Returns:
        Dict[str, Any]: Validation results.
    """
    result = {"is_valid": True, "missing_fields": [], "warnings": []}
    critical_fields = [
        ("tender_meta", "tender_id"),
        ("tender_meta", "tender_title"),
        ("key_dates", "bid_end"),
        ("financial_requirements", "emd"),
    ]

    for section, field in critical_fields:
        section_data = data.get(section, {})
        if not isinstance(section_data, dict):
            section_data = {}
        if is_field_empty(section_data.get(field)):
            result["missing_fields"].append(f"{section}.{field}")
            result["is_valid"] = False
    return result

def validate_extraction_completeness(data: Any, portal_type: str) -> Dict[str, Any]:
    """Route to portal-specific validation and perform final assembly."""
    # Safety check: ensure data is a dict
    if not isinstance(data, dict):
        logger.error(f"Validation failed: Data is not a dictionary but {type(data)}")
        return {
            "is_valid": False,
            "missing_fields": ["root"],
            "warnings": ["CRITICAL: LLM did not return a structured object"],
            "portal_type": portal_type,
            "validation_summary": {"total_issues": 1, "missing_fields_count": 1, "warnings_count": 0}
        }

    logger.info(f"Validating {portal_type} portal extraction")

    if portal_type == "GeM":
        validation = validate_gem_fields(data)
    elif portal_type == "CPPP":
        validation = validate_cppp_fields(data)
    else:
        validation = validate_generic_fields(data)

    # Universal critical checks
    meta = data.get("tender_meta", {})
    if not isinstance(meta, dict): meta = {}

    if is_field_empty(meta.get("tender_id")):
        validation["warnings"].append("Tender ID is missing - critical field")

    dates = data.get("key_dates", {})
    if not isinstance(dates, dict): dates = {}

    if is_field_empty(dates.get("bid_end")):
        validation["warnings"].append("Bid end date is missing - critical field")

    validation["portal_type"] = portal_type
    validation["validation_summary"] = {
        "total_issues": len(validation["missing_fields"]) + len(validation["warnings"]),
        "missing_fields_count": len(validation["missing_fields"]),
        "warnings_count": len(validation["warnings"]),
    }

    return validation
