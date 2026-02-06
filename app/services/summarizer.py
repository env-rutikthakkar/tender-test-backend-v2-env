import json
import logging
import os
from typing import List
from fastapi import UploadFile

from app.services.pdf_extractor import (
    extract_text_and_links,
    fetch_external_pdfs
)
from app.services.rule_parser import (
    extract_structured_fields,
    extract_critical_sections
)
from app.services.groq_client import (
    call_groq_with_retry,
    validate_json_response,
    estimate_tokens
)
from app.services.batch_processor import (
    extract_relevant_lines,
    chunk_text,
    process_micro_batches,
    merge_micro_summaries,
    create_final_prompt
)
from app.services.gap_filler import (
    get_missing_field_summary,
    fill_missing_fields
)
from app.models.schema import TenderSummary, TENDER_SCHEMA

logger = logging.getLogger(__name__)

SINGLE_PASS_TOKEN_LIMIT = 40000
DEFAULT_CONTEXT_BUDGET = 15000

def load_prompt_template() -> str:
    """Load main analysis prompt template."""
    prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/tender_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def prepare_smart_context(full_text: str, rule_data: dict, sections: dict, budget: int = DEFAULT_CONTEXT_BUDGET) -> str:
    """Build optimized context for single-pass LLM calls."""
    context = [f"=== PRE-EXTRACTED DATA ===\n{json.dumps(rule_data, indent=2)}\n\n"]
    if estimate_tokens(full_text) < (budget * 0.9):
        context.append(f"=== COMPLETE TENDER DOCUMENT ===\n{full_text}\n")
        return "".join(context)

    avail = budget - estimate_tokens("".join(context)) - 500
    section_map = [
        ("eligibility", "ELIGIBILITY CRITERIA", 0.25),
        ("financial", "FINANCIAL REQUIREMENTS", 0.25),
        ("timeline", "KEY DATES & TIMELINE", 0.20),
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

async def _run_single_pass(full_text: str, rule_data: dict) -> dict:
    """Single-pass LLM extraction."""
    optimized = prepare_smart_context(full_text, rule_data, extract_critical_sections(full_text))
    prompt = load_prompt_template().replace(
        "{{SCHEMA_JSON}}", json.dumps(TENDER_SCHEMA, indent=2)
    ).replace(
        "{{RULE_EXTRACTED_DATA}}", json.dumps(rule_data, indent=2)
    ).replace(
        "{{TENDER_TEXT}}", optimized
    )
    return _finalize_result(await call_groq_with_retry(prompt))

async def _run_batch_processing(full_text: str, rule_data: dict) -> dict:
    """Multi-level batching for large documents."""
    filtered = extract_relevant_lines(full_text)
    if estimate_tokens(filtered) <= SINGLE_PASS_TOKEN_LIMIT:
        return await _run_single_pass(filtered, rule_data)

    summaries = await process_micro_batches(chunk_text(filtered), call_groq_with_retry)
    combined = merge_micro_summaries(summaries, rule_data)
    prompt = create_final_prompt(combined, json.dumps(TENDER_SCHEMA, indent=2))
    return _finalize_result(await call_groq_with_retry(prompt))

def _finalize_result(llm_response: str) -> dict:
    """Validate and return Pydantic-dumped dict."""
    return TenderSummary(**validate_json_response(llm_response)).model_dump()

async def process_tender_multi_file(pdf_files: List[UploadFile]) -> dict:
    """Combined pipeline for single/multi-file processing."""
    try:
        all_docs, combined_text = [], ""
        for idx, f in enumerate(pdf_files):
            text, links = await extract_text_and_links(await f.read())
            if idx == 0 and links:
                text += "\n\n" + "\n\n".join(await fetch_external_pdfs(links))
            all_docs.append({"filename": f.filename, "content": text})
            combined_text += f"\n\n=== {f.filename} ===\n{text}"

        rule_data = extract_structured_fields(combined_text)
        tokens = estimate_tokens(combined_text)

        summary = await _run_single_pass(combined_text, rule_data) if tokens <= SINGLE_PASS_TOKEN_LIMIT \
                  else await _run_batch_processing(combined_text, rule_data)

        missing = get_missing_field_summary(summary)
        filled = 0
        if missing['critical_missing'] > 0:
            summary = await fill_missing_fields(summary, all_docs)
            filled = missing['critical_missing'] - get_missing_field_summary(summary)['critical_missing']

        summary["_metadata"] = {
            "processing_pipeline": "unified-multi-pass",
            "files_processed": [d["filename"] for d in all_docs],
            "total_tokens": tokens,
            "fields_filled": filled
        }
        return clean_empty_fields(summary)
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise

def clean_empty_fields(data: any) -> any:
    """Recursively remove fields with invalid or 'Not Found' values."""
    INVALID_VALUES = {"not found", "not mentioned", "not specified", "n/a", "", "null", "none"}

    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if k == "_metadata": # Keep metadata as is
                cleaned[k] = v
                continue

            clean_v = clean_empty_fields(v)

            # Check if value is invalid string
            is_invalid_str = isinstance(clean_v, str) and clean_v.lower().strip() in INVALID_VALUES
            # Check if value is empty collection
            is_empty = clean_v is None or (isinstance(clean_v, (list, dict)) and len(clean_v) == 0)

            if not is_invalid_str and not is_empty:
                cleaned[k] = clean_v
        return cleaned
    elif isinstance(data, list):
        cleaned_list = [clean_empty_fields(item) for item in data]
        return [i for i in cleaned_list if i not in (None, "", [], {})]
    return data
