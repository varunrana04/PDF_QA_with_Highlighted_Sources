"""
main.py  —  FastAPI app for PDF Q&A with Highlighted Sources
Endpoints:
  POST /upload          — upload PDF, parse + index
  GET  /query           — SSE stream of answer tokens + citation bboxes
  GET  /pdf/{doc_id}    — serve raw PDF bytes to frontend (for pdf.js)
  GET  /pages/{doc_id}  — return page count + sizes
"""

from __future__ import annotations
import io
import logging
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from pdf_parser import parse_pdf, ParsedPDF
from embedder import build_index, SearchIndex

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Suppress noisy HTTP/404 logs from embedding models checking for optional files
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

# ── Config ────────────────────────────────────────────────────────────────────
MAX_FILE_MB = 500
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="PDF Q&A", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session store  doc_id → {parsed, index} ────────────────────────
sessions: dict[str, dict] = {}


# ── Upload ────────────────────────────────────────────────────────────────────

@app.post("/upload")
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    """
    Parse + index a PDF. Returns doc_id for subsequent requests.
    Fails gracefully on corrupted, oversized, or scanned PDFs.
    """
    # 1. MIME Type check
    if file.content_type != "application/pdf":
        raise HTTPException(415, "Only application/pdf is supported.")

    # 2. Early Content-Length check (from headers)
    cl = request.headers.get("content-length")
    if cl and int(cl) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(413, f"File too large. Max {MAX_FILE_MB} MB.")

    contents = await file.read()
    
    # Magic-byte check
    if not contents.startswith(b'%PDF'):
        raise HTTPException(415, "File does not appear to be a valid PDF (missing %PDF header).")

    mb = len(contents) / (1024 * 1024)
    if mb > MAX_FILE_MB:
        raise HTTPException(413, f"File too large ({mb:.1f} MB). Max {MAX_FILE_MB} MB.")

    # Parse
    parsed: ParsedPDF = parse_pdf(contents)
    if parsed.error and parsed.is_scanned:
        raise HTTPException(422, parsed.error)
    if parsed.error and not parsed.words:
        raise HTTPException(422, parsed.error)

    # Post-parse security checks
    MAX_PAGES = 10000
    if parsed.page_count > MAX_PAGES:
        raise HTTPException(413, f"Document exceeds maximum allowed pages ({MAX_PAGES}).")
    
    MAX_TEXT_MB = 50.0
    text_mb = len(parsed.full_text.encode('utf-8')) / (1024 * 1024)
    if text_mb > MAX_TEXT_MB:
        raise HTTPException(413, f"Extracted text too large ({text_mb:.1f} MB). Max {MAX_TEXT_MB} MB.")

    # Index (may raise if completely empty)
    try:
        index: SearchIndex = build_index(parsed.words)
    except ValueError as e:
        raise HTTPException(422, str(e))

    doc_id = str(uuid.uuid4())
    sessions[doc_id] = {
        "parsed": parsed,
        "index": index,
        "raw_bytes": contents,
        "filename": file.filename or "document.pdf",
    }

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "page_count": parsed.page_count,
        "word_count": len(parsed.words),
        "chunk_count": len(index.chunks),
        "warning": parsed.error,  # non-fatal warnings
        "metadata": {
            "total_pages": parsed.page_count,
            "text_pages": parsed.page_count - parsed.scanned_pages,
            "image_only_pages": parsed.scanned_pages
        }
    }


# ── Serve raw PDF bytes ───────────────────────────────────────────────────────

@app.get("/pdf/{doc_id}")
async def serve_pdf(doc_id: str):
    session = _get_session(doc_id)
    return Response(
        content=session["raw_bytes"],
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{session["filename"]}"'},
    )


# ── Page sizes ────────────────────────────────────────────────────────────────

@app.get("/pages/{doc_id}")
async def page_sizes(doc_id: str):
    session = _get_session(doc_id)
    parsed: ParsedPDF = session["parsed"]
    return {
        "page_count": parsed.page_count,
        "pages": parsed.page_sizes,  # [{w, h}, ...]
    }


# ── SSE Query ─────────────────────────────────────────────────────────────────

@app.get("/query")
async def query(doc_id: str, question: str):
    """
    Stream answer via SSE.
    Each event: data: { type, content | citation }
    """
    from qa_engine import stream_answer

    if not question.strip():
        raise HTTPException(400, "Question is empty.")

    session = _get_session(doc_id)
    index: SearchIndex = session["index"]

    return StreamingResponse(
        stream_answer(question, index),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "sessions": len(sessions)}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_session(doc_id: str) -> dict:
    session = sessions.get(doc_id)
    if not session:
        raise HTTPException(404, "Document not found. Upload first.")
    return session


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
