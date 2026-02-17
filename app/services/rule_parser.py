"""
Rule-Based Field Extraction
Uses regex patterns to extract structured fields BEFORE LLM processing.
"""

import re
import logging
from typing import Dict, Optional, List
from app.services.gem_rules import extract_gem_fields
from app.services.cppp_rules import extract_cppp_fields

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
    """
    Extract a single field from text using a predefined regex pattern.

    Args:
        text (str): The text to search within.
        pattern_key (str): The key in the PATTERNS dictionary.

    Returns:
        Optional[str]: The extracted text or None if not found.
    """
    pattern = PATTERNS.get(pattern_key)
    if not pattern: return None
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1) if match.lastindex else match.group(0)
    return None

def extract_all_dates(text: str) -> List[str]:
    """
    Extract all date-like strings from the document text.

    Args:
        text (str): Document text.

    Returns:
        List[str]: List of unique date strings found.
    """
    dates = []
    for k in ["date_dd_mm_yyyy", "date_dd_mmm_yyyy"]:
        dates.extend(re.findall(PATTERNS[k], text, re.IGNORECASE))
    return list(set(dates))

def detect_portal(text: str) -> str:
    """
    Detect which government portal the tender belongs to using keyword weights.

    Args:
        text (str): Document text.

    Returns:
        str: "GeM", "CPPP", or "Generic".
    """
    gem_score = 0
    cppp_score = 0

    gem_indicators = [
        ("Government e-Marketplace", 2),
        ("GeM Portal", 2),
        ("gem.gov.in", 3),
        ("GEM/202", 3),
        ("बिडर का न्यूनतम", 2),
        ("मूल उपकरण निर्माता", 2),
        ("Buyer Added Terms", 2),
        ("ePBG", 2),
        ("Pre-Qualification Requirement", 1),
        ("Document required from seller", 2),
        ("Item Category", 1),
        ("Total Quantity", 1),
    ]

    cppp_indicators = [
        ("Central Public Procurement Portal", 3),
        ("CPPP", 3),
        ("eprocure.gov.in", 3),
        ("Envelope-1", 2),
        ("Envelope-2", 2),
        ("Date & time of issue", 2),
        ("Due Date & time of Submission", 2),
        ("Online Submission", 1),
        ("Offline Submission", 1),
        ("NIT No", 2),
        ("Technical Proposal", 1),
    ]

    text_lower = text.lower()

    for indicator, weight in gem_indicators:
        if indicator.lower() in text_lower:
            gem_score += weight

    for indicator, weight in cppp_indicators:
        if indicator.lower() in text_lower:
            cppp_score += weight

    logger.info(f"Portal detection - GeM score: {gem_score}, CPPP score: {cppp_score}")

    if gem_score > cppp_score and gem_score >= 2:
        return "GeM"
    elif cppp_score > gem_score and cppp_score >= 2:
        return "CPPP"
    else:
        return "Generic"

def extract_structured_fields(text: str) -> Dict[str, any]:
    """
    Root function to extract fields using regex before LLM processing.
    Routes to portal-specific regex rules.

    Args:
        text (str): Full document text.

    Returns:
        Dict[str, any]: dictionary of regex-extracted fields.
    """
    portal = detect_portal(text)
    logger.info(f"Routing extraction to {portal} extraction logic")

    if portal == "GeM":
        gem_extracted = extract_gem_fields(text)
        return _extract_base_fields(text, portal, gem_extracted)
    elif portal == "CPPP":
        cppp_extracted = extract_cppp_fields(text)
        return _extract_base_fields(text, portal, cppp_extracted)
    else:
        return _extract_base_fields(text, portal, {})

def _extract_base_fields(text: str, portal: str, portal_specific: Dict[str, any]) -> Dict[str, any]:
    """
    Internal helper to extract common fields applicable across all portals.

    Args:
        text (str): Document text.
        portal (str): Detected portal name.
        portal_specific (dict): Fields already extracted by specific rules.

    Returns:
        Dict[str, any]: Merged dictionary of common and specific fields.
    """
    extracted = {"portal": portal}
    extracted.update(portal_specific)

    if "tender_id" not in extracted:
        tid = extract_field(text, "tender_id_gem") or extract_field(text, "tender_id_generic")
        if tid and not re.match(r"^\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}$", tid):
            extracted["tender_id"] = tid

    if "emd" not in extracted:
        emd = extract_field(text, "emd_amount")
        if emd: extracted["emd"] = f"₹{emd}"

    if "tender_fee" not in extracted:
        fee = extract_field(text, "tender_fee")
        if fee: extracted["tender_fee"] = f"₹{fee}"

    for f in ["bid_start", "bid_end", "tech_opening", "financial_opening"]:
        if f not in extracted:
            val = extract_field(text, f"{f}_date" if "bid" in f else f)
            if val: extracted[f] = val

    if "bid_validity" not in extracted:
        bval = extract_field(text, "bid_validity_period")
        if bval: extracted["bid_validity"] = f"{bval} days"

    if "turnover_requirement" not in extracted:
        turnover = extract_field(text, "turnover")
        if turnover: extracted["turnover_requirement"] = f"₹{turnover}"

    if "experience_required" not in extracted:
        exp = extract_field(text, "experience_years")
        proj = extract_field(text, "similar_projects")
        if exp or proj:
            extracted["experience_required"] = " / ".join(filter(None, [f"{exp} years" if exp else None, f"{proj} projects" if proj else None]))

    for k, v in [("msme_exemption", "msme_exemption"), ("startup_exemption", "startup_exemption")]:
        if v not in extracted and re.search(PATTERNS[k], text, re.IGNORECASE):
            extracted[v] = "Yes"

    return extracted

def extract_critical_sections(text: str) -> Dict[str, str]:
    """
    Extract relevant sections of the document to reduce LLM context size.

    Args:
        text (str): Full document text.

    Returns:
        Dict[str, str]: Mapping of section name to extracted text snippet.
    """
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
