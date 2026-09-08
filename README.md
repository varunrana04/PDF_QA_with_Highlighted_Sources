# Context-Aware PDF QA System (RAG)

An enterprise-grade, low-latency Retrieval-Augmented Generation (RAG) engine designed to parse complex PDFs, extract coordinate-aware text chunks, and synthesize highly accurate answers using Google Gemini. Crucially, the system restricts the LLM's knowledge boundary strictly to the retrieved context and maps citations directly back to geometric bounding boxes on the original PDF canvas for visual verification.

## 🏗 System Architecture & Data Flow

1. **Ingestion (`PyMuPDF`)**: Documents are parsed not just for text, but for geometric bounding boxes (`start_y`, `end_y`). 
2. **Semantic Chunking**: A sliding-window chunker aggregates text blocks into 500-token chunks with a 100-token overlap, preserving context continuity while dragging along the associated page coordinates.
3. **Embedding (`all-MiniLM-L6-v2`)**: Chunks are densely encoded into 384-dimensional vectors.
4. **Retrieval (`FAISS`)**: $O(1)$ L2 exact-match similarity search fetches the Top-K most relevant chunks in $< 2\text{ms}$.
5. **Synthesis (`Google Gemini`)**: The LLM is dynamically prompted to answer the user query *exclusively* using the retrieved FAISS chunks. Hallucination is aggressively penalized.
6. **Visualization (`React + Vite`)**: Citations are parsed from the LLM response and mapped back to the parsed bounding boxes, rendering exact overlay highlights on the source document canvas in the browser.

## 🚀 Setup & Installation

### Requirements
- Python 3.10+
- Node.js 18+
- A Google Gemini API Key

### Backend Initialization
```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:
```env
GEMINI_API_KEY=your_api_key_here
```

### Frontend Initialization
```bash
cd frontend
npm install
```

## ⚙️ Running the System
Start the backend API (runs on `http://localhost:8000`):
```bash
cd backend
uvicorn main:app --reload
```

Start the React Frontend (runs on `http://localhost:5173`):
```bash
cd frontend
npm run dev
```

## 🔌 API Specification

### `POST /api/upload`
Uploads a PDF and synchronously initializes the FAISS embedding index in-memory.
**Request:** `multipart/form-data` with file field `file`.
**Response:** `{"message": "File parsed and indexed successfully"}`

### `POST /api/qa`
Queries the FAISS index and synthesizes an answer.
**Request Payload:**
```json
{
  "question": "What is the primary mechanism of attention?"
}
```
**Response Payload:**
```json
{
  "answer": "The primary mechanism is scaled dot-product attention... [page 3]",
  "citations": [3],
  "boxes": {
    "3": [
      {"x0": 50, "y0": 100, "x1": 500, "y1": 150}
    ]
  }
}
```

## 📂 Samples
Check the `samples/` directory for example inputs (`sample_input.pdf`) and the resulting JSON inference payload (`sample_output.json`).
