"""
Gap Filler Service
Identifies missing or empty fields in the extraction result and uses targeted LLM calls
to re-extract them from the source documents.
"""

import logging
from typing import Dict, List, Any
from app.services.groq_client import call_groq_with_retry, validate_json_response

logger = logging.getLogger(__name__)

# Configuration of critical fields that require high-confidence extraction
CRITICAL_FIELDS = {
    "key_dates": [
        "bid_end", "bid_start", "publication_date", "bid_validity",
        "pre_bid_meeting_date", "pre_bid_meeting_location",
        "technical_bid_opening", "financial_bid_opening",
        "contract_start", "project_duration",
        "date_and_time_of_issue", "due_date_and_time_of_submission"
    ],
    "financial_requirements": [
        "emd", "tender_fee", "performance_security",
        "payment_terms", "retention_money", "epbg_details"
    ],
    "tender_meta": [
        "tender_title", "portal", "department",
        "issuing_authority", "tender_id", "country", "state",
        "organization_address", "tender_document_date",
        "submission_instructions", "boq_title", "type_of_bid",
        "item_category", "total_quantity"
    ],
    "eligibility_snapshot": [
        "turnover_requirement", "experience_required",
        "who_can_bid", "consortium_or_jv_allowed",
        "international_bidders_allowed",
        "bidder_technical_infrastructure",
        "oem_turnover_requirement", "mse_relaxation", "startup_relaxation",
        "detailed_pre_qualification_criteria"
    ],
    "scope_of_work": [
        "description", "deliverables", "location",
        "duration", "technical_specifications"
    ],
    "legal_and_risk_clauses": [
        "rejection_of_bid", "splitting_of_work", "liquidated_damages",
        "blacklisting_clause", "warranty_period"
    ],
    "additional_important_information": [
        "detailed_evaluation_scoring_criteria",
        "evaluation_method", "bid_to_ra_enabled",
        "technical_clarification_time", "buyer_added_atc"
    ],
    "documents_required": [
        "documents_required", "online_submission_documents",
        "offline_submission_documents"
    ],
    "root": [
        "executive_summary", "pre_qualification_requirement"
    ]
}

EMPTY_INDICATORS = ["", "not mentioned", "n/a", "not specified", "not available", "tbd", None]

def find_missing_fields(data: Dict[str, Any], parent_key: str = "", path: str = "") -> List[Dict[str, Any]]:
    """
    Recursively traverse JSON data to find fields with empty values.

    Args:
        data (Dict[str, Any]): JSON object to scan.
        parent_key (str): Key of the current section.
        path (str): Dot-notated path to the current field.

    Returns:
        List[Dict[str, Any]]: List of missing field metadata.
    """
    missing = []
    for key, value in data.items():
        current_path = f"{path}.{key}" if path else key
        if isinstance(value, dict):
            missing.extend(find_missing_fields(value, key, current_path))
        elif isinstance(value, list):
            if not value or all(not item for item in value):
                missing.append({
                    "section": parent_key or "root",
                    "field": key,
                    "path": current_path,
                    "is_critical": _is_critical_field(parent_key, key)
                })
        elif value is None or (isinstance(value, str) and value.lower().strip() in EMPTY_INDICATORS):
            missing.append({
                "section": parent_key or "root",
                "field": key,
                "path": current_path,
                "is_critical": _is_critical_field(parent_key, key)
            })
    return missing

def _is_critical_field(section: str, field: str) -> bool:
    """Helper to check if a field is critical."""
    return section in CRITICAL_FIELDS and field in CRITICAL_FIELDS[section]

async def fill_missing_fields(draft_json: Dict[str, Any], documents: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    High-level entry point for re-extracting missing critical fields.

    Args:
        draft_json (Dict[str, Any]): Current extraction state.
        documents (List[Dict[str, str]]): Source document texts.

    Returns:
        Dict[str, Any]: Updated JSON with gaps filled.
    """
    try:
        missing = find_missing_fields(draft_json)
        critical = [m for m in missing if m["is_critical"]]

        if not critical:
            return draft_json

        logger.info(f"Attempting to fill {len(critical)} critical gaps")
        filled_data = await _execute_gap_extraction(critical, documents)
        return _deep_merge(draft_json, filled_data)
    except Exception as e:
        logger.error(f"Gap filling failed: {str(e)}")
        return draft_json

async def _execute_gap_extraction(missing_fields: List[Dict], documents: List[Dict[str, str]]) -> Dict[str, Any]:
    """Internal task for targeted LLM extraction."""
    field_list = "\n".join([f"- {m['path']}" for m in missing_fields])
    doc_context = "\n".join([f"--- Doc: {d['filename']} ---\n{d['content'][:15000]}" for d in documents])

    prompt = f"""You are a tender analyst. We have some missing fields from a previous extraction pass.
Please search the document text below and extract EXACT values for these specific paths.

MISSING FIELDS:
{field_list}

DOCUMENT CONTEXT (Truncated):
{doc_context}

INSTRUCTIONS:
1. Search specifically for these fields by path.
2. If found, provide the exact corresponding value.
3. If still not found, use "Not mentioned".
4. Output valid JSON matching the path structure.
"""
    res = await call_groq_with_retry(prompt)
    return validate_json_response(res)

def _deep_merge(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge updates into base dictionary without overwriting valid data with empty data."""
    result = base.copy()
    for key, value in updates.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = _deep_merge(result[key], value)
        elif value not in EMPTY_INDICATORS:
            result[key] = value
    return result

def get_missing_field_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate summary of missing fields for validation and logging."""
    missing = find_missing_fields(data)
    sections = {}
    for m in missing:
        s = m["section"]
        sections[s] = sections.get(s, 0) + 1

    return {
        "total_missing": len(missing),
        "critical_missing": len([m for m in missing if m["is_critical"]]),
        "by_section": sections
    }
