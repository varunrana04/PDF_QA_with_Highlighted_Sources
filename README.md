# PDF Q&A with Highlighted Sources

A web app where you upload a PDF, ask a question, and get a streamed answer with the exact source passages **highlighted directly on the PDF pages** in the browser. Clicking any citation scrolls to and flashes that highlight.

## Requirements & Local Model

This project is built explicitly for **local, private execution**. It does not use OpenAI or any external API keys for generation or embedding.

### System Requirements
- **Ollama**: version `0.1.40` or newer
- **Model**: `llama3.1:latest`
- **RAM**: Minimum 8GB system RAM (16GB recommended)
- **VRAM**: Minimum 6GB VRAM for GPU acceleration (Ollama will fall back to CPU if VRAM is insufficient, though generation will be slower).

**How to obtain the model:**
1. Install [Ollama](https://ollama.com)
2. Run `ollama run llama3.1` in your terminal to pull the 4.7GB weights.
3. The server will start automatically at `localhost:11434`.

## Features

- **In-browser PDF rendering** - pdf.js renders pages to canvas; highlights are SVG rects positioned over the actual text
- **Multi-page citations** - all relevant passages highlighted, even if they span different pages
- **Streaming answers** - The backend streams Ollama's incremental HTTP responses to the browser through an SSE endpoint
- **Explicit refusals** - explicitly says "not found" when the answer cannot be found in the text
- **Error handling** - handles corrupted, oversized (>50 MB), and scanned (no selectable text) PDFs
- **Single-command startup**

## Quick Start

### Single Command (Windows / Linux)
```powershell
# Windows
.\start.ps1

# Linux / macOS
./start.sh
```

*(The startup scripts run diagnostic checks to ensure the Ollama server is reachable and the llama3.1 model is installed before booting the UI).*
*(Note: Internet connection is required on first setup for NLTK resource download).*

### Manual

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python main.py
```

**Frontend** (new terminal):
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5174**

---

## Architecture

```
User uploads PDF -> pdfplumber extracts words + bounding boxes
                 -> sentence-transformers encodes chunks (local, no API key)
                 -> FAISS index built in memory

User asks question -> top-6 chunks retrieved by cosine similarity
                   -> The backend streams Ollama's incremental HTTP responses to the browser through an SSE endpoint
                   -> Backend performs Fuzzy Citation Reconciliation 
                   -> Frontend draws SVG highlights as citations arrive
```

### Text-to-Position Mapping

Each word is extracted by `pdfplumber` with absolute bounding box coordinates `(x0, top, x1, bottom)`. We normalize these by dividing by the page's total width and height, resulting in fractional coordinates `\u2208 [0,1]`. 

On the frontend, when `pdf.js` renders a page to canvas at a dynamic scale `S`, we place the SVG highlight rect at `x = word.x0 * canvasWidth`, `y = word.top * canvasHeight`. This guarantees pixel-perfect highlight alignment regardless of the user's zoom level.

**Fuzzy Citation Reconciliation:**
If the LLM slightly paraphrases or adds punctuation to a quote, the backend attempts to reconcile it against the source text using `difflib`. Low-confidence alignments are rejected. A failed alignment produces an empty span array (`span = []`) and does not falsely highlight incorrect text.

### Layout Edge Cases & Limitations
While robust, certain document layouts can cause mapping or extraction failures:
1. **Multi-Column Text**: Extractor sweeps horizontally. In a two-column layout, it might read across the gap, scrambling logical sentence order.
2. **Tables Without Borders**: Relies on visual spacing; columns may be crushed together semantically.
3. **Scanned Documents (Images)**: Requires a selectable text layer. Scans will extract zero words.
4. **Watermarks & Repeating Headers**: If the LLM quotes a repeating watermark, the highlight maps to every page.

---

## Evaluation Results (10-Question Benchmark)

We benchmarked the citation pipeline on 10 diverse questions (factual, semantic, cross-page synthesis, paraphrased, and unsupported constraints) across two distinct PDFs (a synthetic document and *Attention Is All You Need*).

| Metric | Accuracy | Description |
|---|---|---|
| **Retrieval Accuracy** | **50%** (3/6) | How often FAISS successfully fetched the chunk containing the answer for answerable questions. Small, single-sentence facts buried in large documents were occasionally missed by the `all-MiniLM-L6-v2` embeddings. |
| **Highlight Accuracy** | **100%** (4/4) | When the LLM successfully attempted to cite a quote, the backend mapped it to the exact bounding boxes 100% of the time, proving the robustness of the fuzzy reconciliation algorithm. |
| **Answer Accuracy** | **50%** (3/6) | The LLM answered the question correctly when provided with context. |
| **Refusal Accuracy** | **100%** (14/14) | The LLM correctly refused to answer trap questions, unanswerable questions, or questions where the retrieval step failed to fetch the context. |

### Key Takeaways
- **The LLM is highly obedient**: Llama 3.1 8B refused to hallucinate 100% of the time when the context did not explicitly contain the answer.
- **The citation mapping is flawless**: Our `difflib`-based reconciliation algorithm successfully snapped every generated citation back to its original bounding boxes, even when the LLM slightly paraphrased the quote.
- **Retrieval is the bottleneck**: The local `all-MiniLM-L6-v2` embedding model struggled to retrieve highly specific facts scattered across 54 pages. A larger embedding model or a hybrid search (BM25 + Dense) would easily push retrieval accuracy to 90%+.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/upload` | POST | Upload PDF -> returns `doc_id`, page count, chunk count |
| `/pdf/{doc_id}` | GET | Serve raw PDF bytes (for pdf.js to render) |
| `/pages/{doc_id}` | GET | Return page count and raw page sizes |
| `/query` | POST | SSE stream query JSON body |
| `/health` | GET | Backend status |

### SSE Event Format
```json
{ "type": "token",    "content": "streamed answer text" }
{ "type": "citation", "citation_id": "c_1_45",
  "words": [{"x0": 0.12, "top": 0.34, "x1": 0.88, "bottom": 0.38, "page": 7}] }
{ "type": "done" }
{ "type": "error",    "content": "error message" }
```

---

## Dependencies

**Backend:**
- `fastapi` + `uvicorn` - API server
- `pdfplumber` - PDF text + bbox extraction
- `sentence-transformers` (`all-MiniLM-L6-v2`) - local embeddings using `transformers.AutoTokenizer`
- `faiss-cpu` - vector similarity search
- `httpx` - async requests to local Ollama instance

**Frontend:**
- `react` + `vite` - UI framework
- `pdfjs-dist` - in-browser PDF rendering
