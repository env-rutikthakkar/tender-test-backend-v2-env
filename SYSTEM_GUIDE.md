# Tender AI - Backend Architecture & Detailed Flow

This system processes government tender documents (PDFs) into structured JSON summaries using Groq Cloud's LGU-powered inference.

## 🚀 High-Level Architecture
```text
PDF Upload → Multi-Pass Extraction → LLM Analysis → Gap Filling → API Result
```

## 📂 System Components

### 1. API Layer (`app/api/tender.py`)
- **Endpoint**: `POST /tender/process`
  - Accepts a `List[UploadFile]` for single or multiple PDFs.
  - Returns a unified summary with a `_metadata` block describing the pipeline performance.

### 2. Processing Engine (`app/services/summarizer.py`)
This is the central orchestrator that decides which extraction strategy to use based on document size and complexity.

---

## 🛠 Detailed Internal Flow

### Step 1: Ingestion & Smart Extraction
- **Text Conversion**: `pdf_extractor.py` uses `PyMuPDF` for high-speed text extraction.
- **Link Following**: The system scans for external PDF links (common in government NITs) and automatically fetches/extracts their content to ensure no crucial annexures are missed.
- **Content Unification**: Multiple files are merged with clear boundary markers (e.g., `=== Filename ===`) so the LLM understands the source of each section.

### Step 2: Rule-Based "Ground Truth" Pre-Extraction
- Before calling the LLM, `rule_parser.py` runs optimized Regex patterns to find:
  - **Tender IDs & Portals**: GeM/CPPP specific patterns.
  - **Financials**: EMD, Tender fees, and Performance Security.
  - **Critical Dates**: Bid start, end, and opening dates using date-aware regex.
- **Benefit**: This "Ground Truth" is passed to the LLM to prevent hallucinations of core data.

### Step 3: Strategy Selection (The 40k Token Rule)
The system estimates the total token count of the combined text:
- **Single-Pass Analysis**: If tokens < 40,000, it builds a "Smart Context" by prioritizing critical sections (Eligibility, Scope, etc.) and executes a single high-context LLM call.
- **Hierarchical Batching**: For massive documents (> 40k tokens), the system:
  1. Splits text into manageable chunks.
  2. Runs **Micro-Summaries** on all chunks in parallel.
  3. Merges micro-summaries into a "Master Context" for final structural analysis.

### Step 4: LLM Analysis (Groq LPU)
- **Prompting**: Uses a detailed system prompt that enforces strict JSON schema adherence.
- **Inference**: Powered by high-throughput LPUs via `groq_client.py`.
- **Infrastructure**: Includes Token-Bucket rate limiting (TPM/RPM) to handle high-concurrency without 429 errors.

### Step 5: Active Gap Filling (Deep Search)
- Post-analysis, the system performs a **Gap Check** against the required schema.
- If critical fields (like `Bid End Date` or `Turnover`) are marked as "Not mentioned", it triggers `gap_filler.py`.
- **Deep Search**: A targeted "hunt" prompt is sent to the LLM, focusing specifically on finding the missing pieces across the full raw text using flexible variation matching (synonyms).

### Step 6: Validation & Finalization
- **Pydantic Validation**: Ensures the final JSON matches the `TenderSummary` model.
- **Metadata**: Appends processing stats (tokens used, fields filled, pipeline versions).
- **Output**: Returns the structured summary directly to the API response.
