"""
Rule-Based Field Extraction
Uses regex patterns to extract structured fields BEFORE LLM processing
Critical for cost optimization and accuracy
"""

import re
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


# Regex Patterns for Common Tender Fields
PATTERNS = {
    "tender_id_gem": r"GEM/\d{4}/[A-Z]/\d+",
    "tender_id_generic": r"(?:Tender\s+(?:No|ID|Reference)|Ref(?:\.?\s*No)?|NIT\s*(?:No|ID|Ref)?|Solicitation\s+No)[\s:]+\s*([A-Z0-9\-_/]{4,})",
    "emd_amount": r"(?:EMD|Earnest\s+Money(?:\s+Deposit)?)\s*[:\-]?\s*₹?\s*(?:Rs\.?)?\s*([\d,]+(?:\.\d{2})?)\s*(?:Lakhs?|Crores?|/-)?",
    "tender_fee": r"(?:Tender\s+(?:Fee|Document\s+Fee))\s*[:\-]?\s*₹?\s*(?:Rs\.?)?\s*([\d,]+(?:\.\d{2})?)",
    "performance_security": r"(?:Performance\s+(?:Security|Bank\s+Guarantee|Guarantee))\s*[:\-]?\s*(\d+%|\d+\s*%|₹\s*[\d,]+)",
    "date_dd_mm_yyyy": r"\b(\d{2}[-/\.]\d{2}[-/\.]\d{4})\b",
    "date_dd_mmm_yyyy": r"\b(\d{2}[-\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s]\d{4})\b",
    "bid_end_date": r"(?:Bid\s+(?:Submission\s+)?(?:End|Closing)\s+Date(?:/Time)?)\s*[:\-]?\s*(\d{2}[-/\.]\d{2}[-/\.]\d{4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)",
    "bid_start_date": r"(?:Bid\s+(?:Submission\s+)?(?:Start|Opening|Open)\s+Date(?:/Time)?)\s*[:\-]?\s*(\d{2}[-/\.]\d{2}[-/\.]\d{4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)",
    "tech_opening": r"(?:Technical\s+Bid\s+Opening(?:/Time)?)\s*[:\-]?\s*(\d{2}[-/\.]\d{2}[-/\.]\d{4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)",
    "financial_opening": r"(?:Financial\s+Bid\s+Opening(?:/Time)?)\s*[:\-]?\s*(\d{2}[-/\.]\d{2}[-/\.]\d{4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)",
    "bid_validity_period": r"(?:Bid\s+(?:Offer\s+)?Validity(?:\s+\(From\s+End\s+Date\))?)\s*[:\-]?\s*(\d+)",
    "turnover": r"(?:Annual\s+)?Turnover\s*[:\-]?\s*(?:of\s+)?₹?\s*(?:Rs\.?)?\s*([\d,]+(?:\.\d{2})?)\s*(?:Lakhs?|Crores?)",
    "experience_years": r"(?:Experience\s+of\s+|Minimum\s+)(\d+)\s+(?:years?|yrs)",
    "similar_projects": r"(\d+)\s+similar\s+(?:projects?|works?|contracts?)",
    "portal_gem": r"Government\s+e-?Marketplace|GeM\s+Portal|gem\.gov\.in",
    "portal_cppp": r"Central\s+Public\s+Procurement\s+Portal|CPPP|eprocure\.gov\.in",
    "msme_exemption": r"MSMEs?\s+(?:are\s+)?exempt(?:ed)?|(?:EMD|Earnest\s+Money)\s+exemption\s+for\s+MSMEs?",
    "startup_exemption": r"Startups?\s+(?:are\s+)?exempt(?:ed)?|exemption\s+for\s+Startups?",
    "local_content": r"(?:Local\s+Content|Make\s+in\s+India|Minimum\s+Local\s+Content)\s*[:\-]?\s*(\d+%|\d+\s*%)",
    "consortium_allowed": r"(?:Consortium|Joint\s+Venture|JV)\s+(?:is\s+)?(?:allowed|permitted|not\s+allowed|not\s+permitted)",
}

def extract_field(text: str, pattern_key: str) -> Optional[str]:
    """Extract a single field using regex."""
    pattern = PATTERNS.get(pattern_key)
    if not pattern: return None
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1) if match.lastindex else match.group(0)
    return None

def extract_all_dates(text: str) -> List[str]:
    """Extract all dates from text."""
    dates = []
    for k in ["date_dd_mm_yyyy", "date_dd_mmm_yyyy"]:
        dates.extend(re.findall(PATTERNS[k], text, re.IGNORECASE))
    return list(set(dates))

def extract_structured_fields(text: str) -> Dict[str, any]:
    """Extract known fields using regex before LLM processing."""
    extracted = {}

    # ID & Portal
    tid = extract_field(text, "tender_id_gem") or extract_field(text, "tender_id_generic")

    # Only skip if it's perfectly a date; otherwise, keep it as a potential ID
    if tid:
        if not re.match(r"^\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}$", tid):
            extracted["tender_id"] = tid

    if re.search(PATTERNS["portal_gem"], text, re.IGNORECASE): extracted["portal"] = "GeM"
    elif re.search(PATTERNS["portal_cppp"], text, re.IGNORECASE): extracted["portal"] = "CPPP"

    # Financials
    emd = extract_field(text, "emd_amount")
    if emd: extracted["emd"] = f"₹{emd}"
    fee = extract_field(text, "tender_fee")
    if fee: extracted["tender_fee"] = f"₹{fee}"

    # Dates
    for f in ["bid_start", "bid_end", "tech_opening", "financial_opening"]:
        val = extract_field(text, f"{f}_date" if "bid" in f else f)
        if val: extracted[f] = val

    bval = extract_field(text, "bid_validity_period")
    if bval: extracted["bid_validity"] = f"{bval} days"

    # Eligibility & Performance
    turnover = extract_field(text, "turnover")
    if turnover: extracted["turnover_requirement"] = f"₹{turnover}"

    exp = extract_field(text, "experience_years")
    proj = extract_field(text, "similar_projects")
    if exp or proj:
        extracted["experience_required"] = " / ".join(filter(None, [f"{exp} years" if exp else None, f"{proj} projects" if proj else None]))

    for k, v in [("msme_exemption", "msme_exemption"), ("startup_exemption", "startup_exemption")]:
        if re.search(PATTERNS[k], text, re.IGNORECASE): extracted[v] = "Yes"

    return extracted

def extract_critical_sections(text: str) -> Dict[str, str]:
    """Extract key document sections to focus LLM analysis."""
    sections = {}
    pats = {
        "eligibility": r"(?:Eligibility|Qualification|Who Can Bid).*?\n(.*?)(?=\n\s*\d+\.|\Z)",
        "financial": r"(?:Financial Requirements?|EMD|Tender Fee).*?\n(.*?)(?=\n\s*\d+\.|\Z)",
        "scope_of_work": r"(?:Scope of Work|Technical Specs?).*?\n(.*?)(?=\n\s*\d+\.|\Z)",
        "terms_conditions": r"(?:Terms and Conditions|Special Conditions).*?\n(.*?)(?=\n\s*\d+\.|\Z)",
        "timeline": r"(?:Important Dates?|Timeline|Schedule).*?\n(.*?)(?=\n\s*\d+\.|\Z)",
    }
    for name, pat in pats.items():
        match = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if match: sections[name] = match.group(1).strip()[:5000]
    return sections
