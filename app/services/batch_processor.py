import logging
import asyncio
import json
from typing import List, Dict

logger = logging.getLogger(__name__)

# Keywords for Level 1 relevance filtering
IMPORTANT_KEYWORDS = [
    "tender", "project", "procurement", "contract", "rfp", "nit", "scope",
    "eligibility", "qualification", "bidder", "vendor", "similar work", "supplier",
    "emd", "deposit", "fee", "budget", "turnover", "experience", "financial", "payment"
]

def extract_relevant_lines(text: str) -> str:
    """Minimal filtering: removes only empty lines to preserve context."""
    return "\n".join([line for line in text.splitlines() if line.strip()])

def chunk_text(text: str, max_chars: int = 8000) -> List[str]:
    """Split text into chunks for LLM processing."""
    chunks, current, current_len = [], [], 0
    for line in text.splitlines():
        if current_len + len(line) > max_chars and current:
            chunks.append("\n".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks

MICRO_SUMMARY_PROMPT = """You are a tender extraction specialist. Extract ALL important information from this section.

**CRITICAL FIELDS TO FIND:**
- IDs, Titles, Dates (Start, End, Opening), Validity
- Fees (EMD, Tender Fee), Security, Payments
- Eligibility (MSE, Startup, Turnover, Experience)
- Scope, Location, Duration, Documents

**INSTRUCTIONS:**
- Extract EXACT values/dates as they appear.
- Include TIME if available with dates.
- Use bullet points: Field Name: Value

**Section:**
<<<
{CHUNK}
>>>

Output only bullet points:"""

async def process_micro_batches(chunks: List[str], groq_func, max_concurrent: int = 20) -> List[str]:
    """Process chunks concurrently using a semaphore."""
    semaphore = asyncio.Semaphore(max_concurrent)
    async def process_chunk(chunk):
        async with semaphore:
            try:
                return await groq_func(MICRO_SUMMARY_PROMPT.format(CHUNK=chunk))
            except Exception as e:
                return f"[Error: {str(e)}]"
    return await asyncio.gather(*[process_chunk(c) for c in chunks])

def merge_micro_summaries(summaries: List[str], rule_data: Dict, max_chars: int = 50000) -> str:
    """Combine structured data and micro-summaries into final analysis context."""
    context = [f"=== PRE-EXTRACTED DATA ===\n{json.dumps(rule_data)}\n"]
    budget = max_chars - len("".join(context)) - 500
    for i, s in enumerate(summaries, 1):
        snippet = f"\n--- Section {i} ---\n{s}"
        if len("".join(context)) + len(snippet) < budget:
            context.append(snippet)
        else: break
    return "\n".join(context)

FINAL_STRUCTURED_PROMPT = """You are an expert tender analyst. Create a comprehensive tender summary from the extracted information below.

**CRITICAL FIELDS THAT MUST BE FILLED (search exhaustively in the context):**
- ✅ **consortium_or_jv_allowed** - Search for: "consortium", "joint venture", "JV", "partnership", "tie-up", "collaboration"
- ✅ **bid_end** - Search for: "Bid End Date/Time", "last date", "closing date", "deadline"
- ✅ **bid_start** - Search for: "Bid Opening Date/Time", "bid opening", "opening date", "tender start"
- ✅ **bid_validity** - Search for: "Bid Offer Validity", "bid validity", "validity of bid"
- ✅ **payment_terms** - Search for: "payment schedule", "payment terms", "payment conditions", "billing terms"
- ✅ **pre_bid_meeting_date** - Search for: "pre-bid meeting", "prebid", "clarification meeting", "vendor meeting"
- ✅ **pre_bid_meeting_location** - Search for: "meeting venue", "meeting location", "meeting address", "venue"
- ✅ **tender_fee** - Search for: "document fee", "tender fee", "processing fee", "bid fee", "cost of document"
- ✅ **emd** - Search for: "EMD", "earnest money", "bid security", "security deposit", "bid bond"
- ✅ **tender_title** - Search for: "tender for", "project name", "work description", "subject"
- ✅ **department** - Search for: "department", "ministry", "organization", "issued by"
- ✅ **turnover_requirement** - Search for: "turnover", "financial capacity", "annual turnover", "average turnover"
- ✅ **experience_required** - Search for: "experience", "similar work", "past projects", "completed projects"

**EXTRACTION RULES:**
1. Use EXACT values from the context below - don't invent or assume
2. For dates: Use the exact format as found in document. **IMPORTANT: Include the TIME (e.g., HH:MM:SS) if it is mentioned next to the date.**
3. For amounts: Include currency symbol (₹)
4. Search for fields using ALL possible variations and synonyms
5. IMPORTANT: Look through EVERY section carefully - the context contains extracted data from the full tender document
6. If you see related information for a field (even if not exact match), USE IT
7. Better to extract partial/related info than write "Not mentioned"
8. Only use "Not mentioned" if you've checked ALL sections and truly found nothing
9. Cross-reference between sections - information may be split across multiple parts
10. Pay special attention to lines with dates, amounts, and titles - these are critical

**OUTPUT SCHEMA:**
{SCHEMA_JSON}

**EXTRACTED CONTEXT FROM TENDER DOCUMENT:**
<<<
{COMBINED_CONTEXT}
>>>

**INSTRUCTIONS:**
Now create a comprehensive JSON object matching the schema above. Extract MAXIMUM information.
Return ONLY valid JSON (no markdown, no code blocks, no explanations).

JSON:"""

def create_final_prompt(context: str, schema: str) -> str:
    """Create the final prompt for structured output."""
    return FINAL_STRUCTURED_PROMPT.replace("{COMBINED_CONTEXT}", context).replace("{SCHEMA_JSON}", schema)
