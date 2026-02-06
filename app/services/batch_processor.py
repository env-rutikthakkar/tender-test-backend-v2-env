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
- Eligibility (MSE, Startup, Turnover, Experience, Credentials)
- Scope, Location, Duration
- **Organization Address**, Tel, Fax, Email
- **Rejection of Bid** & **Disqualification Criteria**
- **Offline Submissions** (Hardcopy) & **Online Submissions** (Scanned)
- **Minimum Requirements at Bidder's End** (Infrastructure)
- **6.2 Pre-Qualification/Eligibility Criteria** & **6.3 Evaluation/ Scoring criteria**
- **Executive Summary** (Project overview)
- **Submission Instructions** (Offline address, labels)

**INSTRUCTION:**
- If you find a table (e.g., Eligibility Table, Scoring Table, Document List), **DO NOT SUMMARIZE IT**. Instead, extract the **RAW DATA** from that table exactly as it appears.
- Capture all numbered sections (e.g., "1.1 Offline Submissions", "3.6 Minimum Requirements", "6.2 Eligibility", "6.3 Scoring").
- Vendors need the EXACT criteria to make a decision.

**GeM PORTAL PRE-QUALIFICATION REQUIREMENT (if applicable):**
- Minimum Average Annual Turnover (For 3 Years) - look for "बिडर का न्यूनतम औसत वार्षिक टर्नओवर" - extract EXACT value like "45 Lakh (s)"
- OEM Average Turnover (Last 3 Years) - look for "मूल उपकरण निर्माता का औसत टर्नओवर" - extract EXACT value
- Years of Past Experience Required - look for "समान सेवा के लिए अपेक्षित विगत अनुभव के वर्ष" - extract EXACT value like "3 Year (s)"
- MSE Exemption - look for "एमएसएमई को छूट", values: "Yes" or "No"
- Startup Exemption - look for "स्टार्टअप के लिए छूट", values: "Yes" or "No"
- Document required from seller - look for "विक्रेता से मांगे गए दस्तावेज़" - COPY ENTIRE TEXT EXACTLY

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
- ✅ **organization_address** - Search for: "Corporate Office", "Registered Office", "Headquarters"
- ✅ **organization_telephone** - Search for: "Tel", "Phone", "Contact No" near address
- ✅ **organization_fax** - Search for: "Fax", "Facsimile" near address
- ✅ **tender_document_date** - Search for: "Dated:", "NIT Date"
- ✅ **detailed_pre_qualification_criteria** - Search for: "6.2 Pre-Qualification/Eligibility Criteria", "Eligibility Criteria", "Qualifying Requirements"
- ✅ **detailed_evaluation_scoring_criteria** - Search for: "6.3 Evaluation/ Scoring criteria", "Evaluation Criteria", "Weightage", "Scoring System"
- ✅ **executive_summary** - Summarize the whole project in 3-4 sentences.
- ✅ **submission_instructions** - Search for offline submission address, envelope labels, physical filing rules.

**ELIGIBILITY INSTRUCTIONS:**
- **Capture Complex Logic**: Extract multiple scenarios (e.g., "For 1st Call", "Option A OR Option B").
- **Identify Exclusions**: Note what is NOT accepted (e.g., "Payment certificate will not be treated as credential").
- **Bidder Infrastructure**: Look for "Minimum Requirements at Bidder's End" (Computer, DSC, etc.).

**LEGAL & REJECTION INSTRUCTIONS:**
- **Rejection of Bid**: Search for "Acceptance/Rejection of bids", "Disqualification", "Bids liable for rejection". Include "Right to reject without assigning reason" and "Right to split work" clauses.

**DOCUMENT EXTRACTION INSTRUCTIONS:**
- **offline_submission_documents**: Extract items listed under "Offline Submissions" (Hardcopy/Physical).
- **online_submission_documents**: Extract items listed under "Online Submissions" (Scanned/PDF).
- **documents_required**: Consolidated list of ALL documents.

**GeM PORTAL PRE-QUALIFICATION REQUIREMENT (ONLY if portal is "GeM"):**
If this tender is from GeM (Government e-Marketplace), populate `pre_qualification_requirement` as a SINGLE FORMATTED STRING containing ALL pre-qualification info EXACTLY as it appears in the document:

Format it as:
"Minimum Average Annual Turnover: [value] | OEM Average Turnover: [value] | Years of Experience Required: [value] | MSE Exemption: [value] | Startup Exemption: [value] | Documents Required from Seller: [exact full text from PDF including asterisk notes]"

**CRITICAL - Documents Required from Seller:**
Look for the table row "विक्रेता से मांगे गए दस्तावेज़/Document required from seller" and copy the ENTIRE content including:
- All document names: "Experience Criteria,Past Performance,Bidder Turnover,Certificate (Requested in ATC),OEM Authorization Certificate,OEM Annual Turnover,Compliance of BoQ specification and supporting document"
- AND the asterisk note: "*In case any bidder is seeking exemption from Experience / Turnover Criteria, the supporting documents to prove his eligibility for exemption must be uploaded for evaluation by the buyer"

**IMPORTANT:**
- Extract EXACT values as they appear in PDF (e.g., "45 Lakh (s)", "3 Year (s)", "No", "Yes")
- For "Documents Required from Seller" - copy the COMPLETE text EXACTLY including the asterisk (*) note
- Do NOT summarize, rephrase, or modify ANY values - use exact text from document

**NOTE:** For non-GeM portals, leave `pre_qualification_requirement` as empty string "".

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
