"""
Portal-Specific Validation
Validates that all portal-required fields are present and populated.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# GeM-required fields
GEM_REQUIRED_FIELDS = {
    "tender_meta": ["tender_id", "tender_title", "portal", "item_category", "total_quantity", "boq_title"],
    "eligibility_snapshot": ["turnover_requirement", "oem_turnover_requirement", "experience_required"],
    "financial_requirements": ["epbg_details"],
    "additional_important_information": ["evaluation_method", "bid_to_ra_enabled", "technical_clarification_time", "buyer_added_atc"],
    "root": ["pre_qualification_requirement"]
}

# CPPP-required fields
CPPP_REQUIRED_FIELDS = {
    "tender_meta": ["tender_id", "tender_title", "portal"],
    "key_dates": ["date_and_time_of_issue", "due_date_and_time_of_submission"],
    "documents_required": ["online_submission_documents", "offline_submission_documents"],
    "eligibility_snapshot": ["bidder_technical_infrastructure"],
}

EMPTY_INDICATORS = ["not found", "not mentioned", "not specified", "n/a", "", None]


def is_field_empty(value: Any) -> bool:
    """Check if a field value is considered empty."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.lower().strip() in EMPTY_INDICATORS
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def validate_gem_fields(data: dict) -> Dict[str, Any]:
    """
    Validate GeM-specific fields are present and populated.
    Returns validation result with missing fields.
    """
    result = {
        "is_valid": True,
        "missing_fields": [],
        "warnings": []
    }

    for section, fields in GEM_REQUIRED_FIELDS.items():
        if section == "root":
            section_data = data
        else:
            section_data = data.get(section, {})

        for field in fields:
            value = section_data.get(field)
            if is_field_empty(value):
                result["missing_fields"].append(f"{section}.{field}")
                result["is_valid"] = False
                logger.warning(f"GeM validation: Missing/empty field {section}.{field}")

    # GeM-specific warnings
    pre_qual = data.get("pre_qualification_requirement", "")
    if is_field_empty(pre_qual):
        result["warnings"].append("pre_qualification_requirement is empty - GeM tenders MUST have this")

    documents = data.get("documents_required", {}).get("documents_required", [])
    if not documents or len(documents) == 0:
        result["warnings"].append("documents_required is empty - should contain pre-qual documents")

    return result


def validate_cppp_fields(data: dict) -> Dict[str, Any]:
    """
    Validate CPPP-specific fields are present and populated.
    Returns validation result with missing fields.
    """
    result = {
        "is_valid": True,
        "missing_fields": [],
        "warnings": []
    }

    for section, fields in CPPP_REQUIRED_FIELDS.items():
        if section == "root":
            section_data = data
        else:
            section_data = data.get(section, {})

        for field in fields:
            value = section_data.get(field)
            if is_field_empty(value):
                result["missing_fields"].append(f"{section}.{field}")
                result["is_valid"] = False
                logger.warning(f"CPPP validation: Missing/empty field {section}.{field}")

    # CPPP-specific warnings
    online_docs = data.get("documents_required", {}).get("online_submission_documents", [])
    offline_docs = data.get("documents_required", {}).get("offline_submission_documents", [])

    if not online_docs or len(online_docs) == 0:
        result["warnings"].append("online_submission_documents is empty - CPPP tenders must separate online docs")

    if not offline_docs or len(offline_docs) == 0:
        result["warnings"].append("offline_submission_documents is empty - check if physical submission is required")

    date_issue = data.get("key_dates", {}).get("date_and_time_of_issue")
    date_due = data.get("key_dates", {}).get("due_date_and_time_of_submission")
    if is_field_empty(date_issue) or is_field_empty(date_due):
        result["warnings"].append("CPPP date fields should have specific labels - verify extraction")

    return result


def validate_generic_fields(data: dict) -> Dict[str, Any]:
    """
    Validate common fields for generic portals.
    """
    result = {
        "is_valid": True,
        "missing_fields": [],
        "warnings": []
    }

    # Check critical common fields
    critical_fields = [
        ("tender_meta", "tender_id"),
        ("tender_meta", "tender_title"),
        ("key_dates", "bid_end"),
        ("financial_requirements", "emd"),
    ]

    for section, field in critical_fields:
        section_data = data.get(section, {})
        value = section_data.get(field)
        if is_field_empty(value):
            result["missing_fields"].append(f"{section}.{field}")
            result["is_valid"] = False

    return result


def validate_portal_specific_fields(data: dict, portal_type: str) -> Dict[str, Any]:
    """
    Route to portal-specific validation based on detected portal type.
    """
    logger.info(f"Validating {portal_type} portal extraction")

    if portal_type == "GeM":
        return validate_gem_fields(data)
    elif portal_type == "CPPP":
        return validate_cppp_fields(data)
    else:
        return validate_generic_fields(data)


def validate_extraction_completeness(data: dict, portal_type: str) -> Dict[str, Any]:
    """
    Comprehensive validation including:
    1. Portal-specific field presence
    2. Field value quality
    3. Cross-field consistency
    """
    validation = validate_portal_specific_fields(data, portal_type)

    # Additional checks
    tender_id = data.get("tender_meta", {}).get("tender_id", "")
    if is_field_empty(tender_id):
        validation["warnings"].append("Tender ID is missing - this is a critical field")

    bid_end = data.get("key_dates", {}).get("bid_end", "")
    if is_field_empty(bid_end):
        validation["warnings"].append("Bid end date is missing - this is critical for bidding timeline")

    # Portal-specific cross-checks
    if portal_type == "GeM":
        # Check that pre_qualification_requirement has all components
        pre_qual = data.get("pre_qualification_requirement", "")
        if isinstance(pre_qual, str) and "|" not in pre_qual:
            validation["warnings"].append("pre_qualification_requirement format may be incomplete (missing | separators)")

    elif portal_type == "CPPP":
        # Check envelope separation
        online = data.get("documents_required", {}).get("online_submission_documents", [])
        offline = data.get("documents_required", {}).get("offline_submission_documents", [])
        if not online and not offline:
            validation["warnings"].append("Neither online nor offline submission documents found - envelope structure may not be extracted")

    validation["portal_type"] = portal_type
    validation["validation_summary"] = {
        "total_issues": len(validation["missing_fields"]) + len(validation["warnings"]),
        "missing_fields_count": len(validation["missing_fields"]),
        "warnings_count": len(validation["warnings"]),
    }

    return validation
