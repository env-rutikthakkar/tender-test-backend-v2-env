from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import logging

from app.services.summarizer import process_tender_multi_file

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tender", tags=["tender"])

@router.post("/process", response_model=dict)
async def process_tender_api(
    pdf_files: List[UploadFile] = File(..., description="Single or multiple tender PDF files")
):
    """Process one or more tender PDFs and return a structured summary."""
    try:
        if not pdf_files:
            raise HTTPException(status_code=400, detail="At least one PDF file required")
        if len(pdf_files) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 files allowed")

        for f in pdf_files:
            if not f.filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"Invalid file: {f.filename}")

        summary = await process_tender_multi_file(pdf_files)

        tender_id = summary.get("tender_meta", {}).get("tender_id", "")

        return {
            "status": "success",
            "tender_id": tender_id,
            "summary": summary,
            "metadata": summary.get("_metadata", {}),
            "message": "Tender(s) processed and summarized successfully"
        }
    except Exception as e:
        logger.error(f"Process failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
