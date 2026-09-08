# System Architecture

## Overview
The PDF QA System is a standard Retrieval-Augmented Generation (RAG) web application. It consists of a React frontend and a FastAPI backend.

## Components
1. **Frontend (React + Vite)**:
   - Provides a chat interface for users to submit questions.
   - Renders a side-by-side split screen to display PDF pages corresponding to citations.
2. **Backend API (FastAPI)**:
   - Provides `/api/qa` endpoint for answering questions.
   - Serves the PDF file for the frontend to render.
3. **Retrieval Engine (FAISS + HuggingFace)**:
   - Extracts semantic embeddings from text chunks.
   - Performs low-latency similarity searches.
4. **Generator (Google Gemini)**:
   - Synthesizes the final answer using strictly the context retrieved by FAISS.

## Data Flow
1. **Initialization**: The PDF is parsed, chunked, embedded, and stored in a local FAISS index on server startup.
2. **Query**: The user submits a question via the React frontend.
3. **Retrieval**: The backend embeds the query and fetches the Top-K most similar text chunks from the FAISS index.
4. **Generation**: The backend injects the context chunks into the LLM prompt. The LLM generates the answer and cites the page numbers.
5. **Response**: The frontend displays the answer and makes the citations clickable, which highlights the relevant passages on the PDF canvas.
