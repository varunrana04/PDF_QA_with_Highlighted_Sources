"""
embedder.py
Chunks PDF text, embeds chunks with sentence-transformers (local, no API key),
builds a FAISS index, and retrieves the top-k chunks for a query.

Each chunk carries a list of "word spans" — the Word objects whose text
overlaps with that chunk — so the frontend can draw exact bbox highlights.
"""

from __future__ import annotations
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from pdf_parser import Word

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton model (loaded once per process)
# ---------------------------------------------------------------------------
_model: Optional[SentenceTransformer] = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading sentence-transformer model…")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Model loaded.")
    return _model


# ---------------------------------------------------------------------------
# Chunk data model
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    text: str
    chunk_id: int
    start_word_idx: int   # index into words list
    end_word_idx: int
    pages: list[int] = field(default_factory=list)  # which pages it spans


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------

TARGET_TOKENS = 200
TOKEN_OVERLAP = 50

def chunk_words(words: list[Word]) -> list[Chunk]:
    """
    Split word list into chunks based on token limits.
    Breaks at the nearest sentence boundary under the 200-token cap.
    Only force-cuts mid-sentence if a single sentence exceeds the budget.
    """
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    
    chunks = []
    chunk_id = 1
    
    current_words = []
    current_tokens = 0
    start_idx = 0
    last_sentence_end = -1
    
    i = 0
    while i < len(words):
        word = words[i]
        word_tokens = len(tokenizer.tokenize(word.text))
        
        current_words.append(word)
        current_tokens += word_tokens
        
        if word.text.endswith(('.', '!', '?')):
            last_sentence_end = i
            
        if current_tokens >= TARGET_TOKENS:
            # Cut the chunk
            if last_sentence_end > start_idx and last_sentence_end < i:
                cut_idx = last_sentence_end
            else:
                # Force cut mid-sentence
                cut_idx = i
                
            chunk_words_slice = words[start_idx : cut_idx + 1]
            text = " ".join(w.text for w in chunk_words_slice)
            pages = sorted(set(w.page for w in chunk_words_slice))
            chunks.append(Chunk(
                text=text,
                chunk_id=chunk_id,
                start_word_idx=start_idx,
                end_word_idx=cut_idx + 1,
                pages=pages
            ))
            chunk_id += 1
            
            # Calculate overlap start (try to start at a previous sentence boundary)
            overlap_start = cut_idx + 1 - 25
            for j in range(cut_idx - 1, start_idx, -1):
                if words[j].text.endswith(('.', '!', '?')):
                    overlap_start = j + 1
                    break
            new_start = max(start_idx + 1, overlap_start)
            
            i = new_start
            start_idx = new_start
            current_words = []
            current_tokens = 0
            last_sentence_end = -1
            continue
            
        i += 1
        
    if current_words and len(current_words) > 10:
        text = " ".join(w.text for w in current_words)
        pages = sorted(set(w.page for w in current_words))
        chunks.append(Chunk(
            text=text,
            chunk_id=chunk_id,
            start_word_idx=start_idx,
            end_word_idx=len(words),
            pages=pages,
        ))
        
    return chunks


# ---------------------------------------------------------------------------
# FAISS index
# ---------------------------------------------------------------------------

@dataclass
class SearchIndex:
    chunks: list[Chunk]
    words: list[Word]
    index: faiss.IndexFlatIP   # inner-product on L2-normalised = cosine


def build_index(words: list[Word]) -> SearchIndex:
    """Embed all chunks and build a FAISS index."""
    chunks = chunk_words(words)
    if not chunks:
        raise ValueError("No text chunks to index.")

    model = get_model()
    texts = [c.text for c in chunks]
    logger.info("Embedding %d chunks…", len(chunks))
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype="float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    return SearchIndex(chunks=chunks, words=words, index=index)


def search(search_index: SearchIndex, query: str, k: int = 6) -> list[tuple[Chunk, float]]:
    """Return top-k (chunk, score) pairs for a query string."""
    model = get_model()
    q_emb = model.encode([query], normalize_embeddings=True)
    q_emb = np.array(q_emb, dtype="float32")

    k = min(k, len(search_index.chunks))
    scores, idxs = search_index.index.search(q_emb, k)

    results = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx >= 0 and score >= 0.3:  # Threshold set to 0.3
            results.append((search_index.chunks[idx], float(score)))
    return results


def get_words_for_chunk(search_index: SearchIndex, chunk: Chunk) -> list[Word]:
    """Return the Word objects that belong to a chunk."""
    return search_index.words[chunk.start_word_idx:chunk.end_word_idx]
