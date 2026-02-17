"""
CPPP Portal-Specific Extraction Rules
Handles all CPPP-specific field extraction, including envelope-based documents,
CPPP date formats, and multi-call experience criteria.
"""

import re
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

# CPPP-Specific Regex Patterns
CPPP_PATTERNS = {
    "tender_id": r"(?:NIT|Tender|Reference|Ref)\s*(?:No\.?|Number)?\s*[:\-]?\s*([A-Z0-9\-_/]{4,})",
    "date_and_time_of_issue": r"Date\s*&?\s*[Tt]ime\s+of\s+[Ii]ssue\s*[:\-]?\s*(.+?)(?:\n|$)",
    "due_date_and_time_submission": r"Due\s+Date\s*&?\s*[Tt]ime\s+of\s+[Ss]ubmission\s*[:\-]?\s*(.+?)(?:\n|$)",
    "envelope_1_header": r"Envelope[\s-]*(?:1|One|I)[\s\-:]*(?:Technical|Technical\s+Bid|Technical\s+Proposal)",
    "envelope_2_header": r"Envelope[\s-]*(?:2|Two|II)[\s\-:]*(?:Financial|Financial\s+Bid|Financial\s+Proposal)",
    "envelope_3_header": r"Envelope[\s-]*(?:3|Three|III)[\s\-:]*(?:.*)",
}

def extract_cppp_tender_id(text: str) -> Optional[str]:
    """Extract CPPP-format tender ID (NIT No., etc)."""
    match = re.search(CPPP_PATTERNS["tender_id"], text, re.IGNORECASE)
    if match:
        tid = match.group(1).strip()
        # Avoid extracting pure dates
        if not re.match(r"^\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}$", tid):
            return tid
    return None

def extract_cppp_date_fields(text: str) -> Dict[str, Optional[str]]:
    """Extract CPPP-specific date fields with exact labels."""
    result = {}

    # Date and Time of Issue
    issue_match = re.search(CPPP_PATTERNS["date_and_time_of_issue"], text, re.IGNORECASE)
    if issue_match:
        result["date_and_time_of_issue"] = issue_match.group(1).strip()

    # Due Date and Time of Submission
    due_match = re.search(CPPP_PATTERNS["due_date_and_time_submission"], text, re.IGNORECASE)
    if due_match:
        result["due_date_and_time_of_submission"] = due_match.group(1).strip()

    return result

def extract_cppp_envelope_documents(text: str) -> Dict[str, List[str]]:
    """
    Extract envelope-based document structure.
    Handles Envelope-1 (Technical), Envelope-2 (Financial), and optional Envelope-3.
    """
    result = {
        "online_submission_documents": [],
        "offline_submission_documents": []
    }

    # Find Envelope-1 (Technical/Online)
    envelope_1_pattern = r"Envelope[\s-]*(?:1|One|I).*?(?:Envelope[\s-]*(?:2|Two|II)|$)"
    envelope_1_match = re.search(envelope_1_pattern, text, re.IGNORECASE | re.DOTALL)
    if envelope_1_match:
        envelope_1_text = envelope_1_match.group(0)
        docs = extract_document_list(envelope_1_text)
        if docs:
            result["online_submission_documents"].extend(docs)

    # Find Envelope-2 (Financial/Online or Offline based on context)
    envelope_2_pattern = r"Envelope[\s-]*(?:2|Two|II).*?(?:Envelope[\s-]*(?:3|Three|III)|$)"
    envelope_2_match = re.search(envelope_2_pattern, text, re.IGNORECASE | re.DOTALL)
    if envelope_2_match:
        envelope_2_text = envelope_2_match.group(0)
        docs = extract_document_list(envelope_2_text)
        if docs:
            result["online_submission_documents"].extend(docs)

    # Find Offline submission documents section
    offline_pattern = r"(?:Offline\s+Submission|Hardcopy|Physical\s+Submission).*?(?:\n\n|\Z)"
    offline_match = re.search(offline_pattern, text, re.IGNORECASE | re.DOTALL)
    if offline_match:
        offline_text = offline_match.group(0)
        docs = extract_document_list(offline_text)
        if docs:
            result["offline_submission_documents"] = docs

    # Remove duplicates while preserving order
    result["online_submission_documents"] = list(dict.fromkeys(result["online_submission_documents"]))
    result["offline_submission_documents"] = list(dict.fromkeys(result["offline_submission_documents"]))

    return result

def extract_document_list(text: str) -> List[str]:
    """Extract document names from envelope or submission section."""
    documents = []

    # Match patterns like:
    # - Document Name
    # 1. Document Name
    # • Document Name
    patterns = [
        r"^\s*[-•]\s*(.+?)$",  # Bullet points
        r"^\s*\d+\.\s*(.+?)$",  # Numbered lists
        r"^([A-Z][^:\n]*?)(?:\s*[-:]\s*(.+))?$",  # Capitalized items
    ]

    for line in text.split('\n'):
        line = line.strip()
        if not line or len(line) < 3:
            continue

        for pattern in patterns:
            match = re.search(pattern, line, re.MULTILINE)
            if match:
                doc = match.group(1).strip()
                # Filter out noise
                if len(doc) > 3 and not doc.lower() in ['', 'instructions', 'note', 'notes']:
                    documents.append(doc)
                    break

    return documents

def extract_cppp_multi_call_experience(text: str) -> Optional[str]:
    """
    Extract multi-call experience criteria for CPPP.
    Handles: 1st Call, 2nd Call, 3rd Call criteria.
    """
    patterns = [
        r"Experience\s+(?:Requirement|Criteria).*?(?:1st|First|Call\s+1).*?([\d\s\w\.]+?)(?:(?:2nd|Second|Call\s+2)|$)",
        r"(?:1st|First)\s+Call\s*[:\-]?\s*([\d\s\w\.]+?)(?:(?:2nd|Second)|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

    return None

def extract_cppp_bidder_infrastructure(text: str) -> Dict[str, Optional[str]]:
    """
    Extract bidder technical infrastructure requirements.
    Includes: Computer System, Broadband, DSC (Digital Signature Certificate).
    """
    result = {}

    # Computer System
    computer_pattern = r"(?:Computer\s+System|Computer\s+Requirement)\s*[:\-]?\s*(.+?)(?:\n|$)"
    computer_match = re.search(computer_pattern, text, re.IGNORECASE)
    if computer_match:
        result["computer_system"] = computer_match.group(1).strip()

    # Broadband
    broadband_pattern = r"(?:Broadband|Internet\s+Connection|Bandwidth)\s*[:\-]?\s*(.+?)(?:\n|$)"
    broadband_match = re.search(broadband_pattern, text, re.IGNORECASE)
    if broadband_match:
        result["broadband"] = broadband_match.group(1).strip()

    # DSC
    dsc_pattern = r"(?:DSC|Digital\s+Signature\s+Certificate)\s*[:\-]?\s*(.+?)(?:\n|$)"
    dsc_match = re.search(dsc_pattern, text, re.IGNORECASE)
    if dsc_match:
        result["dsc"] = dsc_match.group(1).strip()

    return result

def extract_cppp_right_to_reject(text: str) -> Optional[str]:
    """
    Extract "Right to Reject without Reason" clause.
    CPPP-specific clause that allows rejecting bids without providing reasons.
    """
    patterns = [
        r"Right\s+to\s+Reject\s+(?:Bid|Bids)\s+(?:without\s+)?(?:Reason|Assigning\s+Reason).*?(?:\n|$)",
        r"(?:Tenders|Bids)\s+(?:can|may)\s+be\s+rejected\s+without\s+assigning\s+reason",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return "Yes"

    return None

def extract_cppp_split_work(text: str) -> Optional[str]:
    """
    Extract "Right to Split Work" clause.
    CPPP-specific clause allowing work to be split among multiple bidders.
    """
    patterns = [
        r"Right\s+to\s+Split\s+(?:Tender|Work|Project).*?(?:\n|$)",
        r"Work\s+may\s+be\s+split\s+(?:among|between)",
        r"Splitting\s+(?:of\s+)?(?:Tender|Work)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return "Yes"

    return None

def extract_cppp_fields(text: str) -> Dict[str, any]:
    """
    Extract all CPPP-specific fields.
    This is the main entry point for CPPP extraction.
    """
    extracted = {}

    # Tender ID
    tender_id = extract_cppp_tender_id(text)
    if tender_id:
        extracted["tender_id"] = tender_id

    # CPPP-Specific Date Fields
    date_fields = extract_cppp_date_fields(text)
    extracted.update(date_fields)

    # Envelope-based documents
    envelope_docs = extract_cppp_envelope_documents(text)
    extracted.update(envelope_docs)

    # Multi-call experience
    multi_call = extract_cppp_multi_call_experience(text)
    if multi_call:
        extracted["experience_required_multi_call"] = multi_call

    # Bidder infrastructure
    infrastructure = extract_cppp_bidder_infrastructure(text)
    if infrastructure:
        extracted["bidder_technical_infrastructure"] = " | ".join(
            [f"{k}: {v}" for k, v in infrastructure.items() if v]
        )

    # Right to reject
    reject = extract_cppp_right_to_reject(text)
    if reject:
        extracted["rejection_of_bid"] = "Yes"

    # Right to split
    split = extract_cppp_split_work(text)
    if split:
        extracted["splitting_of_work"] = "Yes"

    logger.info(f"CPPP extraction completed. Extracted fields: {list(extracted.keys())}")
    return extracted
