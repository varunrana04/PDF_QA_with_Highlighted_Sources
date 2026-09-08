# High Level Design

## Core Modules
1. **Document Processor**: Handles the ingestion of PDF files. It extracts text and spatial metadata (bounding boxes).
2. **Chunking Engine**: Splits the extracted text into semantically cohesive blocks (overlapping chunks) while preserving the page number and spatial coordinates in the metadata.
3. **Vector Database**: A FAISS index that stores the dense vector embeddings of the text chunks.
4. **LLM Controller**: Interfaces with the Google Gemini model. It handles prompt construction, context injection, and parsing the LLM's response to extract citations.

## Interfaces
- **`/api/qa`**: Expects a JSON payload `{"question": "..."}` and returns `{"answer": "...", "citations": [page1, ...]}`.
- **WebSocket (optional)**: For streaming the LLM's generation token-by-token (currently synchronous HTTP).
