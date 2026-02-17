"""
Batch Processor for Large Documents
Handles chunking, micro-summarization, and merging for large PDFs that exceed LLM context limits.
"""

import asyncio
import logging
from typing import List, Dict, Any
from app.services.groq_client import call_groq_with_retry, validate_json_response, estimate_tokens, rate_limiter

logger = logging.getLogger(__name__)

# Prompt Templates
MICRO_SUMMARY_PROMPT = """You are a tender analyst. Summarize the following document chunk.
Focus on: Eligibility, Financials, Dates, Scope of Work, and Specific Clauses.
Keep it dense and structured.

CHUNK:
{text}
"""

FINAL_MERGE_PROMPT = """You are a tender analyst. Below are micro-summaries of various parts of a tender document along with some pre-extracted structured fields.
Your task is to create a SINGLE, COMPLETE, and ACCURATE JSON summary following the EXACT schema provided.

PRE-EXTRACTED DATA:
{pre_extracted}

MICRO-SUMMARIES:
{summaries}

OUTPUT SCHEMA:
{schema}

DIRECTIONS:
1. Merge all information into a single coherent summary.
2. If there are conflicting values, prefer the most recent or specific one.
3. If information is missing, use empty strings/lists as per schema.
4. Output ONLY valid JSON.
"""

def filter_relevant_lines(text: str) -> str:
    """
    Remove empty lines and boilerplate to reduce token count.

    Args:
        text (str): Raw text.

    Returns:
        str: Filtered text.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return "\n".join(lines)

def chunk_text(text: str, chunk_size: int = 8000) -> List[str]:
    """
    Split text into chunks of roughly equal size for parallel processing.

    Args:
        text (str): Input text.
        chunk_size (int): Max characters per chunk.

    Returns:
        List[str]: List of text chunks.
    """
    chunks = []
    current_chunk = []
    current_size = 0

    for line in text.split('\n'):
        if current_size + len(line) > chunk_size and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_size = 0
        current_chunk.append(line)
        current_size += len(line) + 1

    if current_chunk:
        chunks.append("\n".join(current_chunk))
    return chunks

async def process_micro_batch(chunk: str) -> str:
    """
    Process a single chunk to get a micro-summary.

    Args:
        chunk (str): Text chunk.

    Returns:
        str: Micro-summary text.
    """
    tokens = estimate_tokens(chunk)
    await rate_limiter.wait_for_capacity(tokens + 1000)

    prompt = MICRO_SUMMARY_PROMPT.format(text=chunk)
    res = await call_groq_with_retry(prompt)
    try:
        data = validate_json_response(res)
        return str(data)
    except:
        return res

async def process_large_document(text: str, pre_extracted: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrate the processing of a large document.
    1. Chunking
    2. Concurrent micro-summarization
    3. Final structured merge

    Args:
        text (str): Full document text.
        pre_extracted (dict): Regex-extracted fields.
        schema (dict): Target JSON schema for final output.

    Returns:
        Dict[str, Any]: Final merged and structured summary.
    """
    filtered = filter_relevant_lines(text)
    chunks = chunk_text(filtered)

    logger.info(f"Processing large document in {len(chunks)} chunks")

    tasks = [process_micro_batch(c) for c in chunks]
    summaries = await asyncio.gather(*tasks)

    # Second Pass: Merge and structure
    merge_prompt = FINAL_MERGE_PROMPT.format(
        pre_extracted=pre_extracted,
        summaries="\n\n".join([f"--- CHUNK {i+1} ---\n{s}" for i, s in enumerate(summaries)]),
        schema=schema
    )

    tokens = estimate_tokens(merge_prompt)
    await rate_limiter.wait_for_capacity(tokens + 2000)

    final_res = await call_groq_with_retry(merge_prompt)
    return validate_json_response(final_res)
