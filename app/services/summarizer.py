"""
Tender Summarization Orchestrator
Manages the end-to-end pipeline: PDF extraction, portal detection, rule-based parsing,
LLM analysis (single-pass or batch), gap filling, and validation.
"""

import json
import logging
import os
from typing import List, Dict, Any
from fastapi import UploadFile

from app.services.pdf_extractor import extract_text_and_links, fetch_external_pdfs
from app.services.rule_parser import extract_structured_fields, extract_critical_sections, detect_portal
from app.services.groq_client import call_groq_with_retry, validate_json_response, estimate_tokens
from app.services.batch_processor import process_large_document
from app.services.gap_filler import get_missing_field_summary, fill_missing_fields
from app.services.portal_validator import validate_extraction_completeness
from app.models.schema import TenderSummary, TENDER_SCHEMA

logger = logging.getLogger(__name__)

SINGLE_PASS_TOKEN_LIMIT = 40000
DEFAULT_CONTEXT_BUDGET = 15000

def load_prompt_template(portal_type: str = "Generic") -> str:
    """
    Load the portal-specific prompt template from the prompts directory.

    Args:
        portal_type (str): GeM, CPPP, or Generic.

    Returns:
        str: Prompt template content.
    """
    prompt_map = {
        "GeM": "gem_prompt.txt",
        "CPPP": "cppp_prompt.txt",
        "Generic": "generic_prompt.txt"
    }
    filename = prompt_map.get(portal_type, "generic_prompt.txt")
    prompt_path = os.path.join(os.path.dirname(__file__), "../prompts", filename)

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f"Prompt file {filename} not found, falling back to generic.")
        fallback = os.path.join(os.path.dirname(__file__), "../prompts/generic_prompt.txt")
        with open(fallback, "r", encoding="utf-8") as f:
            return f.read()

def prepare_smart_context(full_text: str, rule_data: Dict, sections: Dict, budget: int = DEFAULT_CONTEXT_BUDGET) -> str:
    """
    Build optimized context for single-pass LLM calls by prioritizing critical sections.

    Args:
        full_text (str): Full raw text.
        rule_data (Dict): Pre-extracted regex fields.
        sections (Dict): Text chunks organized by section headers.
        budget (int): Target token budget for the context.

    Returns:
        str: Formatted context string.
    """
    context = [f"=== PRE-EXTRACTED DATA ===\n{json.dumps(rule_data, indent=2)}\n\n"]
    if estimate_tokens(full_text) < (budget * 0.9):
        context.append(f"=== COMPLETE TENDER DOCUMENT ===\n{full_text}\n")
        return "".join(context)

    avail = budget - estimate_tokens("".join(context)) - 500
    section_map = [
        ("eligibility", "ELIGIBILITY CRITERIA", 0.30),
        ("financial", "FINANCIAL REQUIREMENTS", 0.25),
        ("timeline", "KEY DATES & TIMELINE", 0.15),
        ("scope_of_work", "SCOPE OF WORK", 0.15),
        ("terms_conditions", "TERMS & CONDITIONS", 0.15),
    ]

    for key, title, ratio in section_map:
        if key in sections:
            limit = int(avail * ratio * 5)
            content = sections[key]
            if len(content) > limit:
                half = limit // 2
                content = content[:half] + "\n... [truncated] ...\n" + content[-half:]
            context.append(f"\n=== {title} ===\n{content}\n")
    return "".join(context)

async def _run_single_pass(full_text: str, rule_data: Dict, portal_type: str = "Generic") -> Dict[str, Any]:
    """Execute a single-pass extraction using the full or smart context."""
    optimized = prepare_smart_context(full_text, rule_data, extract_critical_sections(full_text))
    prompt = load_prompt_template(portal_type).replace(
        "{{SCHEMA_JSON}}", json.dumps(TENDER_SCHEMA, indent=2)
    ).replace(
        "{{RULE_EXTRACTED_DATA}}", json.dumps(rule_data, indent=2)
    ).replace(
        "{{TENDER_TEXT}}", optimized
    )
    res = await call_groq_with_retry(prompt)
    return TenderSummary(**validate_json_response(res)).model_dump()

async def process_tender_multi_file(pdf_files: List[UploadFile]) -> Dict[str, Any]:
    """
    Main entry point for processing one or more tender files.
    Coordinates extraction, detection, processing, gap-filling, and validation.
    """
    try:
        all_docs, combined_text = [], ""
        for idx, f in enumerate(pdf_files):
            text, links = await extract_text_and_links(await f.read())
            if idx == 0 and links: # Only follow links from primary document
                ext_texts = await fetch_external_pdfs(links)
                text += "\n\n" + "\n\n".join(ext_texts)
            all_docs.append({"filename": f.filename, "content": text})
            combined_text += f"\n\n=== {f.filename} ===\n{text}"

        portal_type = detect_portal(combined_text)
        rule_data = extract_structured_fields(combined_text)
        tokens = estimate_tokens(combined_text)

        # Strategy selection
        if tokens <= SINGLE_PASS_TOKEN_LIMIT:
            summary = await _run_single_pass(combined_text, rule_data, portal_type)
        else:
            logger.info(f"Using batch processing for large document ({tokens} tokens)")
            res_data = await process_large_document(combined_text, rule_data, TENDER_SCHEMA)
            summary = TenderSummary(**res_data).model_dump()

        # Recursive Gap Filling
        missing = get_missing_field_summary(summary)
        fields_filled_count = 0
        if missing['critical_missing'] > 0:
            logger.info(f"Filling {missing['critical_missing']} gaps for {portal_type}")
            filled_res = await fill_missing_fields(summary, all_docs)
            # Ensure gap-filled result also adheres to schema
            summary = TenderSummary(**filled_res).model_dump()
            new_missing = get_missing_field_summary(summary)
            fields_filled_count = missing['critical_missing'] - new_missing['critical_missing']

        # Validation
        validation = validate_extraction_completeness(summary, portal_type)

        summary["_metadata"] = {
            "portal_type": portal_type,
            "files_processed": [d["filename"] for d in all_docs],
            "total_tokens": tokens,
            "fields_filled": fields_filled_count,
            "validation": validation
        }
        return clean_empty_fields(summary)
    except Exception as e:
        logger.error(f"Summarization pipeline failed: {str(e)}")
        raise

def clean_empty_fields(data: Any) -> Any:
    """
    Recursively remove fields containing 'not mentioned' or empty indicators to clean up the final JSON.
    """
    stop_words = {"not found", "not mentioned", "not specified", "n/a", "", "null", "none"}

    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if k == "_metadata":
                cleaned[k] = v
                continue
            child = clean_empty_fields(v)
            if isinstance(child, str) and child.lower().strip() in stop_words:
                continue
            if child is not None and not (isinstance(child, (list, dict)) and len(child) == 0):
                cleaned[k] = child
        return cleaned
    elif isinstance(data, list):
        items = [clean_empty_fields(i) for i in data]
        return [i for i in items if i not in (None, "", [], {})]
    return data
