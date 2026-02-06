"""
Gap Filler Service
Identifies missing/empty fields and re-extracts them from source documents
"""

import json
import logging
from typing import Dict, List, Any
from app.services.groq_client import call_groq_with_retry, validate_json_response

logger = logging.getLogger(__name__)

# Fields that must be filled (high priority)
CRITICAL_FIELDS = {
    "key_dates": [
        "bid_end", "bid_start", "publication_date", "bid_validity",
        "pre_bid_meeting_date", "pre_bid_meeting_location",
        "technical_bid_opening", "financial_bid_opening",
        "contract_start", "project_duration"
    ],
    "financial_requirements": [
        "emd", "tender_fee", "performance_security",
        "payment_terms", "retention_money"
    ],
    "tender_meta": [
        "tender_title", "portal", "department",
        "issuing_authority", "tender_id", "country", "state",
        "organization_address", "tender_document_date",
        "submission_instructions"
    ],
    "eligibility_snapshot": [
        "turnover_requirement", "experience_required",
        "who_can_bid", "consortium_or_jv_allowed",
        "international_bidders_allowed",
        "bidder_technical_infrastructure",
        "detailed_pre_qualification_criteria"
    ],
    "scope_of_work": [
        "description", "deliverables", "location",
        "duration", "technical_specifications"
    ],
    "legal_and_risk_clauses": [
        "rejection_of_bid", "splitting_of_work"
    ],
    "additional_important_information": [
        "detailed_evaluation_scoring_criteria"
    ],
    "root": [
        "executive_summary"
    ]
}

# Values that indicate missing data
EMPTY_INDICATORS = [
    "",
    "Not mentioned",
    "N/A",
    "Not specified",
    "Not available",
    "TBD",
    "To be announced",
    None
]


def find_missing_fields(data: dict, parent_key: str = "", path: str = "") -> List[Dict[str, str]]:
    """Recursively find empty or missing fields."""
    missing = []
    for key, value in data.items():
        current_path = f"{path}.{key}" if path else key
        if isinstance(value, dict):
            missing.extend(find_missing_fields(value, key, current_path))
        elif isinstance(value, list): continue
        elif value in EMPTY_INDICATORS:
            missing.append({
                "section": parent_key or "root",
                "field": key,
                "path": current_path,
                "current_value": value,
                "is_critical": _is_critical_field(parent_key, key)
            })
    return missing

def _is_critical_field(section: str, field: str) -> bool:
    """Check if field is marked critical."""
    return section in CRITICAL_FIELDS and field in CRITICAL_FIELDS[section]

async def fill_missing_fields(draft_json: dict, all_documents: List[Dict[str, str]]) -> dict:
    """Identify and re-extract missing critical fields from docs."""
    try:
        missing = find_missing_fields(draft_json)
        critical = [m for m in missing if m["is_critical"]]
        if not critical: return draft_json

        filled_data = await _extract_missing_fields(critical, all_documents)
        return _deep_merge(draft_json, filled_data)
    except Exception as e:
        logger.error(f"Gap filling failed: {str(e)}")
        return draft_json

async def _extract_missing_fields(missing_fields: List[Dict], documents: List[Dict[str, str]]) -> dict:
    """Targeted LLM extraction for specific missing fields."""
    field_list = "\n".join([f"- {m['path']}" for m in missing_fields])
    doc_context = _format_documents(documents)

    prompt = f"""You are a tender specialist. Extract exactly these missing fields:
{field_list}

**INSTRUCTIONS:**
- Search for variations (e.g., 'bid_start' can be 'bid opening' or 'start date').
- For dates, include TIME if present.
- Use EXACT values from text.
- Match existing JSON structure.

**DOCUMENTS:**
{doc_context}

Return ONLY valid JSON:"""

    response = await call_groq_with_retry(prompt)
    return validate_json_response(response)


def _format_documents(docs: List[Dict]) -> str:
    """
    Format documents for LLM context with smart truncation.

    Args:
        docs: List of {filename, content} dicts

    Returns:
        Formatted string
    """
    formatted = []
    max_chars_per_doc = 15000  # Limit to avoid token overflow

    for doc in docs:
        content = doc["content"]
        filename = doc["filename"]

        # Truncate if too long
        if len(content) > max_chars_per_doc:
            content = content[:max_chars_per_doc] + "\n... [truncated for length]"

        formatted.append(f"\n{'='*60}\n📄 {filename}\n{'='*60}\n{content}\n")

    return "\n".join(formatted)


def _deep_merge(base: dict, updates: dict) -> dict:
    """
    Recursively merge updates into base dict.

    Args:
        base: Original dict
        updates: Updates to apply

    Returns:
        Merged dict
    """
    result = base.copy()

    for key, value in updates.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            # Recursively merge nested dicts
            result[key] = _deep_merge(result[key], value)
        elif value not in EMPTY_INDICATORS:
            # Only update if new value is not empty
            result[key] = value

    return result


def get_missing_field_summary(data: dict) -> Dict[str, Any]:
    """
    Generate summary of missing fields for logging/debugging.

    Returns:
        Summary statistics
    """
    missing = find_missing_fields(data)

    return {
        "total_missing": len(missing),
        "critical_missing": len([m for m in missing if m["is_critical"]]),
        "missing_by_section": _group_by_section(missing),
        "details": missing
    }


def _group_by_section(missing: List[Dict]) -> Dict[str, int]:
    """Group missing fields by section."""
    sections = {}
    for m in missing:
        section = m["section"]
        sections[section] = sections.get(section, 0) + 1
    return sections
