"""
PDF Text and Link Extraction Service
Uses PyMuPDF (fitz) for fast, accurate extraction - NO LLM
"""

import fitz  # PyMuPDF
import httpx
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)


async def extract_text_and_links(pdf_bytes: bytes) -> Tuple[str, List[str]]:
    """Extract text and external PDF links from a PDF document."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_pages, pdf_links = [], []
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()
            if text.strip(): text_pages.append(f"--- Page {page_num} ---\n{text}")
            for link in page.get_links():
                uri = link.get("uri", "")
                if uri and uri.lower().endswith(".pdf"): pdf_links.append(uri)
        doc.close()
        return "\n\n".join(text_pages), list(set(pdf_links))
    except Exception as e:
        logger.error(f"PDF extraction failed: {str(e)}")
        raise

async def fetch_external_pdfs(links: List[str], timeout: int = 15) -> List[str]:
    """Fetch and extract text from external PDF URLs."""
    extracted = []
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for url in links:
            try:
                res = await client.get(url)
                res.raise_for_status()
                text, _ = await extract_text_and_links(res.content)
                extracted.append(f"\n\n=== External PDF: {url} ===\n{text}")
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {str(e)}")
    return extracted



