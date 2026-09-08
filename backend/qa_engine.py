"""
qa_engine.py
LLM Controller & Generative Synthesis Module

Constructs rigid context-bound prompts using retrieved FAISS chunks and interfaces
with Ollama (Llama 3) to synthesize exact answers. 
To prevent hallucination, the generation boundary is tightly sealed.
It parses citation arrays from the generative output and extracts the
linked geometrical bounding boxes for the frontend to render.
"""

import json
import logging
import os
import re
from typing import AsyncIterator
import httpx

from embedder import SearchIndex, search, get_words_for_chunk
from pdf_parser import Word

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a highly intelligent and concise document Q&A assistant.

CRITICAL RULES FOR CITATIONS:
1. You MUST append a citation to the end of EVERY factual claim you make.
2. The citation MUST use exactly this format: [cite:source_id:exact quote]
   Example: The sky is blue [cite:1:The sky appears blue due to Rayleigh scattering.].
3. Inside the citation, you MUST copy the EXACT string of words from the context that supports your claim.
4. NEVER say "According to source 1" or "In the document". Just state the facts directly and beautifully, then append the citation.
5. If the context does not contain the answer, say EXACTLY: "The document does not contain enough information to answer this question." Do not hallucinate.

Think briefly about the most direct and accurate way to answer the question using only the provided context. Do not ramble. Be precise, intelligent, and concise.
"""

def build_prompt(question: str, retrieved: list) -> str:
    context_parts = []
    for i, (chunk, _) in enumerate(retrieved):
        context_parts.append(f'<source id="{i+1}">\n{chunk.text}\n</source>')
    context = "\n\n".join(context_parts)
    return f"<context>\n{context}\n</context>\n\nQuestion: {question}"

import difflib

def find_exact_words(words: list[Word], quote: str) -> list[Word]:
    """Find the exact sub-span of words that matches the quote, ignoring whitespace and punctuation."""
    def alpha_only(s): return re.sub(r'[^a-z0-9]', '', s.lower())
    
    norm_quote = alpha_only(quote)
    if not norm_quote: return words
    
    char_to_word = []
    full_str = ""
    for i, w in enumerate(words):
        text = alpha_only(w.text)
        full_str += text
        for _ in range(len(text)):
            char_to_word.append(i)
            
    idx = full_str.find(norm_quote)
    if idx != -1:
        start_word_idx = char_to_word[idx]
        end_word_idx = char_to_word[idx + len(norm_quote) - 1]
        return words[start_word_idx:end_word_idx + 1]
        
    # Fallback to approximate source-span matching
    matcher = difflib.SequenceMatcher(None, full_str, norm_quote)
    blocks = matcher.get_matching_blocks()
    
    # Calculate total matching characters
    matched_chars = sum(b.size for b in blocks)
    if matched_chars >= 0.5 * len(norm_quote) and len(blocks) > 1:
        # Fuzzy match successful enough. Find bounding box of all matching blocks
        valid_blocks = [b for b in blocks if b.size > 0]
        if valid_blocks:
            first_match_idx = valid_blocks[0].a
            last_match_idx = valid_blocks[-1].a + valid_blocks[-1].size - 1
            if first_match_idx < len(char_to_word) and last_match_idx < len(char_to_word):
                start_word_idx = char_to_word[first_match_idx]
                end_word_idx = char_to_word[last_match_idx]
                return words[start_word_idx:end_word_idx + 1]
                
    # Final Fallback: Citation invalid (source could not be reliably mapped)
    return []


async def stream_answer(
    question: str,
    search_index: SearchIndex,
    k: int = 6,
) -> AsyncIterator[str]:
    """
    Async generator that yields SSE-formatted strings.
    """
    try:
        retrieved = search(search_index, question, k=k)
        if not retrieved:
            yield _sse({"type": "error", "content": "No relevant passages found."})
            return
            
        scores_debug = [{"chunk_id": i+1, "score": float(score)} for i, (chunk, score) in enumerate(retrieved)]
        yield _sse({"type": "debug", "scores": scores_debug, "threshold": 0.3})

        prompt = build_prompt(question, retrieved)
        
        # Map opaque ID S1, S2 back to actual chunks
        opaque_to_chunk = {
            (i + 1): chunk for i, (chunk, _) in enumerate(retrieved)
        }

        # Check for API fallback
        use_fallback = os.environ.get("USE_HOSTED_API_FALLBACK", "false").lower() == "true"
        if use_fallback:
            ollama_url = os.environ.get("HOSTED_API_URL", "http://localhost:11434/api/generate")
        else:
            ollama_url = "http://localhost:11434/api/generate"
            
        payload = {
            "model": "llama3.1",
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": True,
        }

        buffer = ""
        cite_regex = re.compile(r'\s*\[cite:(\d+):([^\]]*)\]\s*')

        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=5.0)) as client:
            max_retries = 3
            for attempt in range(max_retries):
                async with client.stream("POST", ollama_url, json=payload) as response:
                    if response.status_code != 200:
                        if attempt < max_retries - 1:
                            continue  # Retry
                        yield _sse({"type": "error", "content": f"Inference error: {response.status_code}"})
                        return
                    
                    async for chunk_resp in response.aiter_lines():
                        if not chunk_resp.strip():
                            continue
                        
                        data = json.loads(chunk_resp)
                        token = data.get("response", "")
                        buffer += token

                        # Parse and emit any complete citations
                        while True:
                            m = cite_regex.search(buffer)
                            if not m:
                                break
                            before = buffer[:m.start()]
                            
                            if before.endswith(" ") or before == "":
                                pass
                            elif buffer[m.start()-1:m.start()] != " ":
                                before += " "
                            
                            s_id = int(m.group(1))
                            quote = m.group(2)
                            buffer = buffer[m.end():]
                            
                            if buffer and not buffer.startswith(" ") and not buffer.startswith(".") and not buffer.startswith(","):
                                buffer = " " + buffer

                            if before:
                                yield _sse({"type": "token", "content": before})

                            # Server-side citation validation
                            chunk = opaque_to_chunk.get(s_id)
                            if chunk:
                                chunk_words = get_words_for_chunk(search_index, chunk)
                                exact_words = find_exact_words(chunk_words, quote)
                                
                                # Fallback: If LLM hallucinates the quote string but gives a valid source ID,
                                # just highlight the entire chunk so the citation isn't silently dropped!
                                if not exact_words:
                                    exact_words = chunk_words

                                yield _sse({
                                    "type": "citation",
                                    "citation_id": f"c_{s_id}_{m.start()}",
                                    "words": [
                                        {"x0": w.x0, "top": w.top, "x1": w.x1, "bottom": w.bottom, "page": w.page}
                                        for w in exact_words
                                    ],
                                })

                        # State machine buffer flush logic
                        # Hold buffer if it looks like the start of a citation
                        last_cite_start = buffer.rfind('[cite')
                        last_doc_start = buffer.rfind('[Document')
                        
                        hold_idx = max(last_cite_start, last_doc_start)
                        
                        if hold_idx != -1:
                            emit_part = buffer[:hold_idx]
                            buffer = buffer[hold_idx:]
                        else:
                            last_bracket = buffer.rfind('[')
                            
                            # Check if we might be mid-way through writing '[cite' or '[Document'
                            if last_bracket != -1 and ("[cite".startswith(buffer[last_bracket:]) or "[Document".startswith(buffer[last_bracket:])):
                                emit_part = buffer[:last_bracket]
                                buffer = buffer[last_bracket:]
                            else:
                                emit_part = buffer
                                buffer = ""
                        
                        if emit_part:
                            yield _sse({"type": "token", "content": emit_part})
                    
                    break  # Success, exit retry loop

        # Emit anything left in buffer
        if buffer:
            # Strip any complete unclosed cite tags
            clean_buffer = re.sub(r'\[cite[^\]]*\]', '', buffer)
            # Strip any incomplete trailing tags (e.g., "[cite" or "[c")
            clean_buffer = re.sub(r'\[[^\]]*$', '', clean_buffer)
            if clean_buffer.strip():
                yield _sse({"type": "token", "content": clean_buffer})

        yield _sse({"type": "done"})

    except Exception as e:
        logger.error("QA engine error: %s", e, exc_info=True)
        yield _sse({"type": "error", "content": str(e)})


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
