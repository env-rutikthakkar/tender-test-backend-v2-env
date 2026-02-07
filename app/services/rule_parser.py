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

def extract_gem_pre_qualification(text: str) -> Dict[str, str]:
    """Extract GeM pre-qualification requirements from structured table."""
    result = {}

    # Pattern 1: Minimum Average Annual Turnover (Bidder)
    # Look for: "Minimum Average Annual Turnover of the bidder" on one line, value on next
    turnover_pattern = r"Minimum\s+Average\s+Annual\s+Turnover\s+of\s+the\s+bidder.*?\n\s*([\d,]+)\s*(?:Lakh|Crore|LAKH|CRORE)?\s*\(s\)?"
    turnover_match = re.search(turnover_pattern, text, re.IGNORECASE | re.DOTALL)
    if turnover_match:
        result["turnover_requirement"] = f"₹{turnover_match.group(1)} Lakh(s)"

    # Pattern 2: OEM Average Turnover
    # Look for: "OEM Average Turnover (Last 3 Years)" on one line, value on next
    oem_pattern = r"OEM\s+Average\s+Turnover.*?\n\s*([\d,]+)\s*(?:Lakh|Crore|LAKH|CRORE)?\s*\(s\)?"
    oem_match = re.search(oem_pattern, text, re.IGNORECASE | re.DOTALL)
    if oem_match:
        result["oem_turnover_requirement"] = f"₹{oem_match.group(1)} Lakh(s)"

    # Pattern 3: Years of Past Experience Required
    # Look for: "Years of Past Experience Required for same/similar service" followed by value like "3 Year (s)"
    exp_pattern = r"Years?\s+of\s+Past\s+Experience\s+Required.*?\n\s*(\d+)\s*Year\s*\(s\)?"
    exp_match = re.search(exp_pattern, text, re.IGNORECASE | re.DOTALL)
    if exp_match:
        result["experience_required"] = f"{exp_match.group(1)} Year(s)"

    # Pattern 4: MSE Relaxation
    # Look for: "MSE Relaxation..." followed by "Yes | Complete" or similar
    mse_pattern = r"MSE\s+Relaxation\s+for\s+Years.*?\n\s*(Yes|No|Complete|Partial|Exempt)\s*\|\s*(Complete|Partial|Exempt)?"
    mse_match = re.search(mse_pattern, text, re.IGNORECASE | re.DOTALL)
    if mse_match:
        val1 = mse_match.group(1) or ""
        val2 = mse_match.group(2) or ""
        if val2:
            result["mse_relaxation"] = f"{val1} | {val2}"
        else:
            result["mse_relaxation"] = val1

    # Pattern 5: Startup Relaxation
    # Look for: "Startup Relaxation..." followed by value
    startup_pattern = r"Startup\s+Relaxation\s+for\s+Years.*?\n\s*(Yes|No|Complete|Partial|Exempt)\s*\|\s*(Complete|Partial|Exempt)?"
    startup_match = re.search(startup_pattern, text, re.IGNORECASE | re.DOTALL)
    if startup_match:
        val1 = startup_match.group(1) or ""
        val2 = startup_match.group(2) or ""
        if val2:
            result["startup_relaxation"] = f"{val1} | {val2}"
        else:
            result["startup_relaxation"] = val1

    # Pattern 6: Documents Required from Seller (GeM specific)
    # Capture the full documents section
    docs_pattern = r"Document\s+required\s+from\s+seller\s*\n\s*(.*?)(?:\n\s*\*|$)"
    docs_match = re.search(docs_pattern, text, re.IGNORECASE | re.DOTALL)
    if docs_match:
        docs_text = docs_match.group(1).strip()
        # Split by comma and clean
        docs = [d.strip() for d in docs_text.split(',') if d.strip() and len(d.strip()) > 2]
        if docs:
            result["documents_required"] = docs

    return result

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

    # Extract GeM Pre-qualification requirements ONLY FOR GeM PORTALS
    if re.search(PATTERNS["portal_gem"], text, re.IGNORECASE):
        gem_prequalif = extract_gem_pre_qualification(text)
        extracted.update(gem_prequalif)

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
