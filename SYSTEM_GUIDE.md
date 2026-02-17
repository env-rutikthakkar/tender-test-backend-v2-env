# 📖 Tender AI System Guide

This guide explains how our system turns complex tender PDF files into simple, structured data. We follow a 6-step process to ensure accuracy and catch every detail.

---

## � Step-by-Step Flow

### 1. 📤 Upload & Text Reading
When you upload one or more PDFs, the system:
*   **Reads the Text**: Uses high-speed tools to pull every word from your files.
*   **Follows Links**: If the main document has a link to another PDF (like an Annexure), the system automatically follows that link and reads that file too.
*   **Merges Everything**: It combines all the text into one big "project context."

### 2. 🔍 Portal Detection
The system automatically figures out where the tender is from:
*   **GeM**: Government e-Marketplace.
*   **CPPP**: Central Public Procurement Portal.
*   **Generic**: Any other standard PDF format.

### 3. 📝 Rule-Based "Ground Truth"
Before asking the AI, we use fast "Rules" (Regex) to find facts that never change. This is done in both **English and Hindi**:
*   **Tender IDs**: Exact matching of specific ID formats.
*   **Core Dates**: Identifying "Bid End Date" or "Opening Date."
*   **Financials**: Finding "EMD" (Security Deposit) or "Tender Fee" amounts.
*   *Why?* This ensures the AI doesn't "hallucinate" or guess these critical numbers.

### 4. 🧠 Smart AI Analysis (The Brain)
The system chooses the best way to process the document based on its size:
*   **For Normal Documents**: It picks out the most important sections (Eligibility, Scope, Dates) and sends them to the Groq AI for a single, complete summary.
*   **For Massive Documents (100+ pages)**: It splits the document into smaller chapters, summarizes each chapter, and then merges those summaries into one final result.

### 5. 🩹 Active Gap Filling
After the AI finishes, the system checks the result. If a critical field (like "Turnover Requirement") is still says "Not mentioned," the system:
*   **Goes Back**: It re-scans the raw text specifically looking for that one missing piece.
*   **Deep Search**: It uses a specialized "hunt" prompt to find the answer across all pages.

### 6. ✅ Validation & Final Clean
The final step ensures the data is ready for the dashboard:
*   **Portal Check**: It verifies that all fields required by GeM or CPPP are actually there.
*   **Cleanup**: It removes any messy "N/A" or "Not Mentioned" tags, leaving you with only the useful information.
*   **Metadata**: It attaches a summary of how the processing went (e.g., how many files were read).

---

## 🚀 Why This is Powerful
1.  **Catches Everything**: By following links and annexures.
2.  **No Hallucinations**: Because we use "Rules" for facts and AI for understanding.
3.  **Fast**: Powered by Groq LPU technology for near-instant results.
4.  **Simple**: You get a clean JSON or Dashboard view, not a 100-page PDF struggle.
