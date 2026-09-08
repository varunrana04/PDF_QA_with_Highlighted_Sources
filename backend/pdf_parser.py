"""
pdf_parser.py
HFT-Grade Data Ingestion & Geometric Parsing Module

Extracts text and exact geometric bounding boxes from PDF documents using `pdfplumber`.
Instead of lossy text extraction, this module preserves spatial semantics by mapping
every token to normalized [0,1] floating-point coordinate geometries (x0, top, x1, bottom).
These boxes are persisted through the embedding pipeline so the frontend can precisely
render citation highlights regardless of viewport scaling.
"""

from __future__ import annotations
import io
import logging
import concurrent.futures
from dataclasses import dataclass, field
from typing import Optional
import queue

import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Word:
    text: str
    page: int          # 1-indexed
    x0: float          # normalised [0,1]
    top: float         # normalised [0,1]
    x1: float
    bottom: float
    page_width: float  # PDF page units / points — frontend uses this for scaling
    page_height: float
    word_idx: int = -1 # global word index for exact span mapping

@dataclass
class ParsedPDF:
    words: list[Word] = field(default_factory=list)
    full_text: str = ""          # concatenated, used for chunking
    page_count: int = 0
    page_sizes: list[dict] = field(default_factory=list)  # [{w, h}, ...]
    error: Optional[str] = None
    is_scanned: bool = False
    scanned_pages: int = 0


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def _do_parse(file_bytes: bytes) -> ParsedPDF:
    try:
        pdf = pdfplumber.open(io.BytesIO(file_bytes))
    except PDFPasswordIncorrect:
        return ParsedPDF(error="This PDF is password protected. Please decrypt it first.")
    except Exception as e:
        logger.warning("pdfplumber failed to open PDF: %s", e)
        return ParsedPDF(error=f"Could not read PDF: {e}")

    result = ParsedPDF(page_count=len(pdf.pages))
    text_parts: list[str] = []
    global_word_idx = 0
    empty_pages = 0

    for page_num, page in enumerate(pdf.pages, start=1):
        pw, ph = float(page.width), float(page.height)
        result.page_sizes.append({"w": pw, "h": ph})

        try:
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=False,
            )
        except Exception as e:
            logger.warning("Page %d extraction error: %s", page_num, e)
            words = []

        page_text_tokens = []
        for w in words:
            try:
                word = Word(
                    text=w["text"],
                    page=page_num,
                    x0=w["x0"] / pw,
                    top=w["top"] / ph,
                    x1=w["x1"] / pw,
                    bottom=w["bottom"] / ph,
                    page_width=pw,
                    page_height=ph,
                    word_idx=global_word_idx
                )
                result.words.append(word)
                page_text_tokens.append(w["text"])
                global_word_idx += 1
            except (KeyError, ZeroDivisionError):
                continue

        if page_text_tokens:
            text_parts.append(f"[PAGE {page_num}]\n" + " ".join(page_text_tokens))
        else:
            empty_pages += 1

    pdf.close()

    result.scanned_pages = empty_pages
    if empty_pages == len(pdf.pages) and len(pdf.pages) > 0:
        result.is_scanned = True
        result.error = "This PDF appears to be a scanned image with no selectable text. OCR is required to extract content."
        return result
    elif empty_pages > 0:
        result.is_scanned = True
        logger.warning("Detected %d pages without extractable text.", empty_pages)

    result.full_text = "\n\n".join(text_parts)
    return result

import multiprocessing

def _parse_worker(file_bytes, queue):
    try:
        result = _do_parse(file_bytes)
        queue.put(result)
    except Exception as e:
        queue.put(e)

def parse_pdf(file_bytes: bytes, timeout: int = 600) -> ParsedPDF:
    """
    Parse a PDF from raw bytes with a timeout to prevent infinite hangs on corrupted files.
    Uses multiprocessing.Process for true hard-kills.
    """
    ctx = multiprocessing.get_context('spawn')
    queue = ctx.Queue()
    p = ctx.Process(target=_parse_worker, args=(file_bytes, queue))
    p.start()
    try:
        # Prevent deadlock: queue.get() must be called BEFORE p.join() if the object is large.
        res = queue.get(timeout=timeout)
    except queue.Empty:
        p.kill()
        p.join()
        return ParsedPDF(error="PDF parsing timed out. The file may be corrupted or too complex.")
    
    p.join(5)
    
    if isinstance(res, Exception):
        return ParsedPDF(error=f"Unexpected error during parsing: {res}")
    return res
