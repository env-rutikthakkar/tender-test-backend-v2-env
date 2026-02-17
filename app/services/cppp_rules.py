"""
CPPP Portal-Specific Extraction Rules
Handles extraction for CPPP-specific fields including envelope-based documents.
"""

import re
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# CPPP-Specific Regex Patterns
CPPP_PATTERNS = {
    "tender_id": r"(?:NIT|Tender|Reference|Ref)\s*(?:No\.?|Number)?\s*[:\-]?\s*([A-Z0-9\-_/]{4,})",
    "date_and_time_of_issue": r"Date\s*&?\s*[Tt]ime\s+of\s+[Ii]ssue\s*[:\-]?\s*(.+?)(?:\n|$)",
    "due_date_and_time_submission": r"Due\s+Date\s*&?\s*[Tt]ime\s+of\s+[Ss]ubmission\s*[:\-]?\s*(.+?)(?:\n|$)",
}

def extract_cppp_tender_id(text: str) -> Optional[str]:
    """
    Extract CPPP-format tender ID from document text.

    Args:
        text (str): Document text.

    Returns:
        Optional[str]: Extracted ID or None if not found or if it looks like a date.
    """
    match = re.search(CPPP_PATTERNS["tender_id"], text, re.IGNORECASE)
    if match:
        tid = match.group(1).strip()
        if not re.match(r"^\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}$", tid):
            return tid
    return None

def extract_cppp_date_fields(text: str) -> Dict[str, Optional[str]]:
    """
    Extract CPPP-specific date fields (Issue date, Submission date).

    Args:
        text (str): Document text.

    Returns:
        Dict[str, Optional[str]]: Dictionary with date_and_time_of_issue and due_date_and_time_of_submission.
    """
    result = {}

    issue_match = re.search(CPPP_PATTERNS["date_and_time_of_issue"], text, re.IGNORECASE)
    if issue_match:
        result["date_and_time_of_issue"] = issue_match.group(1).strip()

    due_match = re.search(CPPP_PATTERNS["due_date_and_time_submission"], text, re.IGNORECASE)
    if due_match:
        result["due_date_and_time_of_submission"] = due_match.group(1).strip()

    return result

def extract_cppp_envelope_documents(text: str) -> Dict[str, List[str]]:
    """
    Extract document requirements grouped by submission envelope.

    Args:
        text (str): Document text.

    Returns:
        Dict[str, List[str]]: Mapping of submission type to list of document names.
    """
    result = {
        "online_submission_documents": [],
        "offline_submission_documents": []
    }

    env1_match = re.search(r"Envelope[\s-]*(?:1|One|I).*?(?:Envelope[\s-]*(?:2|Two|II)|$)", text, re.IGNORECASE | re.DOTALL)
    if env1_match:
        docs = extract_document_list(env1_match.group(0))
        if docs: result["online_submission_documents"].extend(docs)

    env2_match = re.search(r"Envelope[\s-]*(?:2|Two|II).*?(?:Envelope[\s-]*(?:3|Three|III)|$)", text, re.IGNORECASE | re.DOTALL)
    if env2_match:
        docs = extract_document_list(env2_match.group(0))
        if docs: result["online_submission_documents"].extend(docs)

    offline_match = re.search(r"(?:Offline\s+Submission|Hardcopy|Physical\s+Submission).*?(?:\n\n|\Z)", text, re.IGNORECASE | re.DOTALL)
    if offline_match:
        docs = extract_document_list(offline_match.group(0))
        if docs: result["offline_submission_documents"] = docs

    result["online_submission_documents"] = list(dict.fromkeys(result["online_submission_documents"]))
    result["offline_submission_documents"] = list(dict.fromkeys(result["offline_submission_documents"]))

    return result

def extract_document_list(text: str) -> List[str]:
    """
    Helper to extract a list of documents from a text block.

    Args:
        text (str): Block of text containing document names.

    Returns:
        List[str]: List of cleaned document names.
    """
    documents = []
    patterns = [r"^\s*[-•]\s*(.+?)$", r"^\s*\d+\.\s*(.+?)$", r"^([A-Z][^:\n]*?)(?:\s*[-:]\s*(.+))?$"]

    for line in text.split('\n'):
        line = line.strip()
        if not line or len(line) < 3: continue

        for pattern in patterns:
            match = re.search(pattern, line, re.MULTILINE)
            if match:
                doc = match.group(1).strip()
                if len(doc) > 3 and not doc.lower() in ['instructions', 'note', 'notes']:
                    documents.append(doc)
                    break

    return documents

def extract_cppp_multi_call_experience(text: str) -> Optional[str]:
    """
    Extract multi-call experience criteria (e.g., criteria for 1st vs 2nd call).

    Args:
        text (str): Document text.

    Returns:
        Optional[str]: Extracted criteria or None.
    """
    patterns = [
        r"Experience\s+(?:Requirement|Criteria).*?(?:1st|First|Call\s+1).*?([\d\s\w\.]+?)(?:(?:2nd|Second|Call\s+2)|$)",
        r"(?:1st|First)\s+Call\s*[:\-]?\s*([\d\s\w\.]+?)(?:(?:2nd|Second)|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match: return match.group(1).strip()

    return None

def extract_cppp_bidder_infrastructure(text: str) -> Dict[str, Optional[str]]:
    """
    Extract bidder technical requirements (Computer, Broadband, DSC).

    Args:
        text (str): Document text.

    Returns:
        Dict[str, Optional[str]]: Mapping of requirement type to value.
    """
    result = {}
    pats = {
        "computer_system": r"(?:Computer\s+System|Computer\s+Requirement)\s*[:\-]?\s*(.+?)(?:\n|$)",
        "broadband": r"(?:Broadband|Internet\s+Connection|Bandwidth)\s*[:\-]?\s*(.+?)(?:\n|$)",
        "dsc": r"(?:DSC|Digital\s+Signature\s+Certificate)\s*[:\-]?\s*(.+?)(?:\n|$)"
    }

    for key, pat in pats.items():
        match = re.search(pat, text, re.IGNORECASE)
        if match: result[key] = match.group(1).strip()

    return result

def extract_cppp_right_to_reject(text: str) -> Optional[str]:
    """
    Detect if the 'Right to Reject' clause is present.

    Args:
        text (str): Document text.

    Returns:
        Optional[str]: 'Yes' if found else None.
    """
    patterns = [
        r"Right\s+to\s+Reject\s+(?:Bid|Bids)\s+(?:without\s+)?(?:Reason|Assigning\s+Reason)",
        r"(?:Tenders|Bids)\s+(?:can|may)\s+be\s+rejected\s+without\s+assigning\s+reason"
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE): return "Yes"
    return None

def extract_cppp_split_work(text: str) -> Optional[str]:
    """
    Detect if the 'Right to Split Work' clause is present.

    Args:
        text (str): Document text.

    Returns:
        Optional[str]: 'Yes' if found else None.
    """
    patterns = [r"Right\s+to\s+Split\s+(?:Tender|Work|Project)", r"Work\s+may\s+be\s+split\s+(?:among|between)", r"Splitting\s+(?:of\s+)?(?:Tender|Work)"]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE): return "Yes"
    return None

def extract_cppp_fields(text: str) -> Dict[str, any]:
    """
    Main entry point for CPPP-specific extraction.

    Args:
        text (str): Document text.

    Returns:
        Dict[str, any]: Comprehensive dictionary of extracted CPPP fields.
    """
    extracted = {}

    tender_id = extract_cppp_tender_id(text)
    if tender_id: extracted["tender_id"] = tender_id

    extracted.update(extract_cppp_date_fields(text))
    extracted.update(extract_cppp_envelope_documents(text))

    multi_call = extract_cppp_multi_call_experience(text)
    if multi_call: extracted["experience_required_multi_call"] = multi_call

    infra = extract_cppp_bidder_infrastructure(text)
    if infra:
        extracted["bidder_technical_infrastructure"] = " | ".join([f"{k}: {v}" for k, v in infra.items() if v])

    if extract_cppp_right_to_reject(text): extracted["rejection_of_bid"] = "Yes"
    if extract_cppp_split_work(text): extracted["splitting_of_work"] = "Yes"

    return extracted
