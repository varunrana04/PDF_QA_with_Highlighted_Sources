import pytest
from transformers import AutoTokenizer
from qa_engine import find_exact_words
from pdf_parser import Word

from embedder import chunk_words

def test_tokenizer_bounds():
    """Verify that chunks fit within the 256 token limit for extreme inputs."""
    # Extremely long string without sentence breaks
    long_words = ["supercalifragilisticexpialidocious"] * 100
    # URLs and numbers and non-english
    weird_words = ["https://example.com/very/long/url?param=1&foo=bar"] * 50
    weird_words += ["12345.67890e-12", "こんにちは", "🚀", "&%$#@"] * 30
    # Normal sentences
    normal_words = ["This", "is", "a", "normal", "sentence."] * 60
    
    all_text_parts = long_words + weird_words + normal_words
    words = [Word(w, 1, 0,0,0,0, 100,100) for w in all_text_parts]
    
    chunks = chunk_words(words)
    assert len(chunks) > 0
    
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    
    for c in chunks:
        # SentenceTransformers adds special tokens [CLS] and [SEP], which is +2 tokens
        tokens = tokenizer(c.text)["input_ids"]
        assert len(tokens) <= 256, f"Chunk exceeded 256 tokens! Got {len(tokens)}: {c.text}"

def test_find_exact_words():
    """Verify the exact and fuzzy span extraction logic."""
    words = [
        Word("This", 1, 0,0,0,0, 100,100),
        Word("is", 1, 0,0,0,0, 100,100),
        Word("a", 1, 0,0,0,0, 100,100),
        Word("validated", 1, 0,0,0,0, 100,100),
        Word("fact", 1, 0,0,0,0, 100,100),
        Word("about", 1, 0,0,0,0, 100,100),
        Word("AI.", 1, 0,0,0,0, 100,100)
    ]
    
    # Exact match
    matched = find_exact_words(words, "validated fact")
    assert len(matched) == 2
    assert matched[0].text == "validated"
    assert matched[1].text == "fact"

    # Fuzzy match (LLM added punctuation or slight paraphrase)
    matched_fuzzy = find_exact_words(words, "a validated fact,")
    assert len(matched_fuzzy) == 3
    assert matched_fuzzy[0].text == "a"
    assert matched_fuzzy[2].text == "fact"
    
    # Complete miss falls back to empty list (citation invalid)
    matched_miss = find_exact_words(words, "hallucinated fact")
    assert len(matched_miss) == 0

def test_multi_page_citation():
    """Verify that citations can span across multiple pages without breaking."""
    words = [
        Word("First", 1, 0,0,0,0, 100,100),
        Word("part", 1, 0,0,0,0, 100,100),
        Word("on", 1, 0,0,0,0, 100,100),
        Word("page", 1, 0,0,0,0, 100,100),
        Word("one.", 1, 0,0,0,0, 100,100),
        Word("Second", 2, 0,0,0,0, 100,100),
        Word("part", 2, 0,0,0,0, 100,100),
        Word("on", 2, 0,0,0,0, 100,100),
        Word("page", 2, 0,0,0,0, 100,100),
        Word("two.", 2, 0,0,0,0, 100,100),
    ]
    
    # Citation spans the page boundary
    quote = "page one. Second part"
    matched = find_exact_words(words, quote)
    
    assert len(matched) == 4
    assert matched[0].text == "page"
    assert matched[0].page == 1
    assert matched[-1].text == "part"
    assert matched[-1].page == 2

import os
from fpdf import FPDF
from pdf_parser import parse_pdf
from embedder import build_index, search, get_words_for_chunk

def test_end_to_end_pipeline():
    """End-to-end integration test: parse -> embed -> retrieve -> match."""
    # 1. Create a dummy PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # The target sentence to retrieve
    target_sentence = "The SAP-1 architecture features a very unique accumulator and program counter."
    pdf.multi_cell(0, 10, txt="This is a test document. " * 50 + target_sentence + " And some more text. " * 50)
    pdf_path = "test_e2e.pdf"
    pdf.output(pdf_path)
    
    try:
        # 2. Parse PDF
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        parsed = parse_pdf(pdf_bytes)
        assert parsed.error is None
        assert len(parsed.words) > 0
        
        # 3. Build Search Index
        search_index = build_index(parsed.words)
        assert search_index is not None
        assert search_index.index.ntotal > 0
        
        # 4. Simulate a retrieval
        results = search(search_index, "Tell me about the SAP-1 architecture.", k=1)
        assert len(results) == 1
        chunk, dist = results[0]
        
        # 5. Extract exact words
        chunk_words = get_words_for_chunk(search_index, chunk)
        exact_words = find_exact_words(chunk_words, target_sentence)
        
        # 6. Assertions
        assert len(exact_words) > 0, "Failed to find the exact sentence in the retrieved chunk."
        
        # Check that bounding boxes are valid
        for w in exact_words:
            assert w.page == 1
            assert w.x1 > w.x0
            assert w.bottom > w.top
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

