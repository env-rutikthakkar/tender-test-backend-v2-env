"""
GeM Portal-Specific Extraction Rules
Handles extraction for GeM-specific fields and pre-qualification tables.
"""

import re
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# GeM-Specific Regex Patterns
GEM_PATTERNS = {
    "tender_id": r"GEM/\d{4}/[A-Z]/\d+",
    "boq_title": r"(?:BOQ|Bill\s+of\s+Quantities)\s*[:\-]?\s*(.+?)(?:\n|$)",
    "item_category": r"(?:Item\s+Category|Product\s+Category)\s*[:\-]?\s*(.+?)(?:\n|$)",
    "relevant_categories": r"(?:Relevant\s+Categories\s+selected\s+for\s+notification|अधिसूचना\s+के\s+लिए\s+चयनित\s+प्रासंगिक\s+श्रेणियाँ)\s*[:\-]?\s*(.*?)(?=\n[^\s•\d]|\Z)",
    "total_quantity": r"(?:Total\s+Quantity|Total\s+Qty\.?|Qty\.?)\s*[:\-]?\s*(\d+(?:[,.\d]+)?)",
    "type_of_bid": r"(?:Single|Two)[\s-]*(?:Packet|Part)\s+Bid",
    "epbg_percentage": r"ePBG\s*[:\-]?\s*(\d+%)",
    "epbg_duration": r"ePBG.*?Duration\s*[:\-]?\s*(\d+\s*(?:days?|weeks?|months?))",
}

def extract_gem_tender_id(text: str) -> Optional[str]:
    """
    Extract GeM-specific tender ID format (GEM/YYYY/X/NNNN).

    Args:
        text (str): Document text.

    Returns:
        Optional[str]: Extracted tender ID or None.
    """
    match = re.search(GEM_PATTERNS["tender_id"], text, re.IGNORECASE)
    return match.group(0) if match else None

def extract_gem_boq_info(text: str) -> Dict[str, Optional[str]]:
    """
    Extract BoQ Title, Item Category, and Total Quantity from GeM documents.

    Args:
        text (str): Document text.

    Returns:
        Dict[str, Optional[str]]: Dictionary with boq_title, item_category, total_quantity, type_of_bid.
    """
    result = {}

    boq_match = re.search(GEM_PATTERNS["boq_title"], text, re.IGNORECASE)
    if boq_match:
        result["boq_title"] = boq_match.group(1).strip()

    category_match = re.search(GEM_PATTERNS["item_category"], text, re.IGNORECASE)
    if category_match:
        result["item_category"] = category_match.group(1).strip()

    rel_cat_match = re.search(GEM_PATTERNS["relevant_categories"], text, re.IGNORECASE | re.DOTALL)
    if rel_cat_match:
        raw_cats = rel_cat_match.group(1).strip()
        # Clean up bullets and newlines
        cats = [c.strip() for c in re.split(r'[\n•\-\*]', raw_cats) if c.strip()]
        result["relevant_categories"] = "; ".join(cats)

    qty_match = re.search(GEM_PATTERNS["total_quantity"], text, re.IGNORECASE)
    if qty_match:
        result["total_quantity"] = qty_match.group(1).strip()

    type_match = re.search(GEM_PATTERNS["type_of_bid"], text, re.IGNORECASE)
    if type_match:
        result["type_of_bid"] = type_match.group(0).strip()

    return result

def extract_gem_epbg_details(text: str) -> Optional[str]:
    """
    Extract ePBG percentage and duration.

    Args:
        text (str): Document text.

    Returns:
        Optional[str]: Formatted string with ePBG details or None.
    """
    percentage_match = re.search(GEM_PATTERNS["epbg_percentage"], text, re.IGNORECASE)
    duration_match = re.search(GEM_PATTERNS["epbg_duration"], text, re.IGNORECASE)

    if percentage_match or duration_match:
        parts = []
        if percentage_match:
            parts.append(f"Percentage: {percentage_match.group(1)}")
        if duration_match:
            parts.append(f"Duration: {duration_match.group(1)}")
        return " | ".join(parts) if parts else None

    return None

def extract_gem_pre_qualification_table(text: str) -> Dict[str, any]:
    """
    Extract GeM pre-qualification table data including bilingual Hindi/English headers.

    Args:
        text (str): Document text.

    Returns:
        Dict[str, any]: Extracted pre-qualification fields.
    """
    result = {}

    # turnover
    turnover_patterns = [
        r"Minimum\s+Average\s+Annual\s+Turnover\s+of\s+the\s+bidder.*?\n\s*([\d,]+)\s*(?:Lakh|Crore|LAKH|CRORE)?\s*\(s\)?",
        r"बिडर का न्यूनतम औसत वार्षिक टर्नओवर.*?\n\s*([\d,]+)\s*(?:लाख|करोड़|Lakh|Crore)?\s*\(s\)?",
    ]
    for pattern in turnover_patterns:
        turnover_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if turnover_match:
            result["turnover_requirement"] = f"₹{turnover_match.group(1)} Lakh(s)"
            break

    # OEM turnover
    oem_patterns = [
        r"OEM\s+Average\s+Turnover.*?\n\s*([\d,]+)\s*(?:Lakh|Crore|LAKH|CRORE)?\s*\(s\)?",
        r"मूल उपकरण निर्माता का औसत टर्नओवर.*?\n\s*([\d,]+)\s*(?:लाख|करोड़|Lakh|Crore)?\s*\(s\)?",
    ]
    for pattern in oem_patterns:
        oem_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if oem_match:
            result["oem_turnover_requirement"] = f"₹{oem_match.group(1)} Lakh(s)"
            break

    # Experience
    exp_patterns = [
        r"Years?\s+of\s+Past\s+Experience\s+Required.*?\n\s*(\d+)\s*Year\s*\(s\)?",
        r"समान सेवा के लिए अपेक्षित विगत अनुभव के वर्ष.*?\n\s*(\d+)\s*Year\s*\(s\)?",
    ]
    for pattern in exp_patterns:
        exp_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if exp_match:
            result["experience_required"] = f"{exp_match.group(1)} Year(s)"
            break

    # MSE relaxation
    mse_patterns = [
        r"MSE\s+Relaxation\s+for\s+Years.*?\n\s*(Yes|No|Complete|Partial|Exempt)\s*\|\s*(Complete|Partial|Exempt)?" ,
        r"एमएसएमई को छूट.*?\n\s*(Yes|No|हाँ|नहीं|Complete|Partial|Exempt).*?(?:\||$)",
    ]
    for pattern in mse_patterns:
        mse_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if mse_match:
            val1 = mse_match.group(1) or ""
            val2 = mse_match.group(2) or "" if mse_match.lastindex and mse_match.lastindex >= 2 else ""
            result["mse_relaxation"] = f"{val1} | {val2}" if val2 else val1
            break

    # Startup relaxation
    startup_patterns = [
        r"Startup\s+Relaxation\s+for\s+Years.*?\n\s*(Yes|No|Complete|Partial|Exempt)\s*\|\s*(Complete|Partial|Exempt)?",
        r"स्टार्टअप के लिए छूट.*?\n\s*(Yes|No|हाँ|नहीं|Complete|Partial|Exempt).*?(?:\||$)",
    ]
    for pattern in startup_patterns:
        startup_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if startup_match:
            val1 = startup_match.group(1) or ""
            val2 = startup_match.group(2) or "" if startup_match.lastindex and startup_match.lastindex >= 2 else ""
            result["startup_relaxation"] = f"{val1} | {val2}" if val2 else val1
            break

    # Documents required
    doc_patterns = [
        r"Document\s+required\s+from\s+seller\s*\n\s*(.*?)(?:\n\s*\*|$)",
        r"विक्रेता से मांगे गए दस्तावेज़\s*\n\s*(.*?)(?:\n\s*\*|$)",
    ]
    for pattern in doc_patterns:
        docs_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if docs_match:
            docs_text = docs_match.group(1).strip()
            docs = [d.strip() for d in re.split(r'[,•\n]', docs_text) if d.strip() and len(d.strip()) > 2]
            if docs:
                if "documentation" not in result: result["documentation"] = {}
                result["documentation"]["checklist"] = docs
            break

    return result

def extract_gem_evaluation_method(text: str) -> Optional[str]:
    """
    Extract GeM evaluation method (Item-wise vs Total).

    Args:
        text (str): Document text.

    Returns:
        Optional[str]: Extracted method or None.
    """
    evaluation_patterns = [
        r"Evaluation.*?Method\s*[:\-]?\s*(Item[- ]wise|Total)",
        r"Evaluation.*?Basis\s*[:\-]?\s*(Item[- ]wise|Total)",
    ]
    for pattern in evaluation_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def extract_gem_bid_to_ra(text: str) -> Optional[str]:
    """
    Extract Bid to Reverse Auction enabled status.

    Args:
        text (str): Document text.

    Returns:
        Optional[str]: Enabled status or None.
    """
    patterns = [
        r"Bid\s+to\s+(?:RA|Reverse\s+Auction|Reverse Auction)\s*[:\-]?\s*(Yes|No|Enabled|Disabled)",
        r"Reverse\s+Auction\s*[:\-]?\s*(Yes|No|Enabled|Disabled)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def extract_gem_technical_clarification_time(text: str) -> Optional[str]:
    """
    Extract technical clarification time allowed.

    Args:
        text (str): Document text.

    Returns:
        Optional[str]: Formatted time or None.
    """
    patterns = [
        r"Technical\s+Clarification.*?Time\s*[:\-]?\s*(\d+\s*(?:hours?|days?|minutes?))",
        r"Clarification\s+Response\s+Time\s*[:\-]?\s*(\d+\s*(?:hours?|days?|minutes?))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def extract_gem_buyer_atc(text: str) -> Optional[str]:
    """
    Extract buyer added Terms & Conditions indicator.

    Args:
        text (str): Document text.

    Returns:
        Optional[str]: ATC status or None.
    """
    patterns = [
        r"Buyer\s+Added\s+(?:Terms\s+and\s+Conditions|T\s*&\s*C|ATC)\s*[:\-]?\s*(Yes|No|Present|Absent)",
        r"Buyer\s+Added\s+ATC\s*[:\-]?\s*(Yes|No)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def extract_gem_fields(text: str) -> Dict[str, any]:
    """
    Main entry point for GeM-specific extraction.

    Args:
        text (str): Document text.

    Returns:
        Dict[str, any]: Comprehensive dictionary of extracted GeM fields.
    """
    extracted = {}

    tender_id = extract_gem_tender_id(text)
    if tender_id:
        extracted["tender_id"] = tender_id

    extracted.update(extract_gem_boq_info(text))

    epbg = extract_gem_epbg_details(text)
    if epbg:
        extracted["epbg_details"] = epbg

    extracted.update(extract_gem_pre_qualification_table(text))

    eval_method = extract_gem_evaluation_method(text)
    if eval_method:
        extracted["evaluation_method"] = eval_method

    bid_to_ra = extract_gem_bid_to_ra(text)
    if bid_to_ra:
        extracted["bid_to_ra_enabled"] = bid_to_ra

    tech_time = extract_gem_technical_clarification_time(text)
    if tech_time:
        extracted["technical_clarification_time"] = tech_time

    buyer_atc = extract_gem_buyer_atc(text)
    if buyer_atc:
        extracted["buyer_added_atc"] = buyer_atc

    return extracted
