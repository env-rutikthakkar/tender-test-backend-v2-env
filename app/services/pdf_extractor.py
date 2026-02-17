"""
PDF Text and Link Extraction Service
Uses PyMuPDF (fitz) for high-performance text and hyperlink extraction.
"""

import fitz
import httpx
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

async def extract_text_and_links(pdf_bytes: bytes) -> Tuple[str, List[str]]:
    """
    Extract raw text and external PDF hyperlinks from PDF content.

    Args:
        pdf_bytes (bytes): The binary content of the PDF file.

    Returns:
        Tuple[str, List[str]]: A tuple containing (combined_text, list_of_pdf_links).
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_pages, pdf_links = [], []

        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()
            if text.strip():
                text_pages.append(f"--- Page {page_num} ---\n{text}")

            for link in page.get_links():
                uri = link.get("uri", "")
                if uri and uri.lower().endswith(".pdf"):
                    pdf_links.append(uri)

        doc.close()
        return "\n\n".join(text_pages), list(set(pdf_links))
    except Exception as e:
        logger.error(f"PDF extraction failed: {str(e)}")
        raise

async def fetch_external_pdfs(links: List[str], timeout: int = 15) -> List[str]:
    """
    Fetch external PDFs from the provided links and extract their text.

    Args:
        links (List[str]): List of URLs pointing to PDF documents.
        timeout (int): Request timeout in seconds.

    Returns:
        List[str]: List of extracted text blocks from each external PDF.
    """
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



