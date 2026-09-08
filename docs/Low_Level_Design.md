# Low Level Design

## Parsing Algorithm
Using `PyMuPDF` (fitz):
1. Iterate over `doc.pages()`.
2. Extract text blocks via `page.get_text("blocks")`.
3. Filter out blocks that are too small or appear to be headers/footers based on geometric heuristics.

## Chunking Algorithm
1. Tokens are estimated using simple whitespace splitting.
2. Blocks are accumulated into a string until `chunk_size` (e.g., 500 tokens) is reached.
3. An overlap of `overlap_size` (e.g., 100 tokens) is carried over to the next chunk to preserve context continuity across boundaries.
4. Each chunk stores a list of source page numbers.

## Embedding and Indexing
1. `SentenceTransformer('all-MiniLM-L6-v2')` converts the chunk text into a 384-dimensional dense vector.
2. `faiss.IndexFlatL2(384)` is used for exact nearest-neighbor search. 
3. The index arrays map exactly to the Python list of metadata objects.

## Prompt Engineering
The system prompt strictly bounds the LLM's knowledge:
```text
You are a highly accurate QA bot.
Answer the question based strictly on the context provided below.
If the answer is not contained in the context, say "I don't know".
Always cite the page number at the end of your answer.
```
