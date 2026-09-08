import requests
import json
import time
import os
import sys
import argparse

def upload_pdf(filepath):
    url_upload = "http://localhost:8001/upload"
    print(f"Uploading {filepath}...")
    try:
        with open(filepath, "rb") as f:
            resp = requests.post(url_upload, files={"file": (os.path.basename(filepath), f, "application/pdf")})
        if resp.status_code != 200:
            print(f"Failed to upload: {resp.text}")
            return None
        return resp.json()["doc_id"]
    except Exception as e:
        print(f"Upload error: {e}")
        return None

def run_query(doc_id, question):
    url_query = "http://localhost:8001/query"
    start_t = time.time()
    
    try:
        with requests.get(url_query, params={"doc_id": doc_id, "question": question}, stream=True) as r:
            if r.status_code != 200:
                print(f"Error: {r.status_code}")
                return None, [], 0, None
            
            full_response = ""
            citations = []
            scores_data = None
            
            for line in r.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: "):
                        data = json.loads(decoded[6:])
                        if data["type"] == "token":
                            full_response += data["content"]
                        elif data["type"] == "citation":
                            citations.append(data)
                        elif data["type"] == "error":
                            full_response += f" [ERROR: {data['content']}]"
                        elif data["type"] == "debug":
                            scores_data = data
                            
        elapsed = time.time() - start_t
        return full_response.strip(), citations, elapsed, scores_data
    except Exception as e:
        print(f"Query error: {e}")
        return None, [], 0, None


def generate_synthetic_pdf(pdf_path):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    c = canvas.Canvas(pdf_path, pagesize=letter)
    for i in range(1, 55):
        if i == 8:
            c.drawString(100, 700, "The primary evaluation metric was established as the F1 score in the original design.")
        elif i == 12:
            c.drawString(100, 50, "The breakthrough transformer architecture was first proposed in")
        elif i == 13:
            c.drawString(100, 750, "the seminal paper Attention Is All You Need, fundamentally changing AI.")
        elif i == 25:
            c.drawString(100, 700, "Research was led by a team of scientists, but the paper explicitly does not disclose their funding sources.")
        elif i == 37:
            c.drawString(100, 700, "Despite earlier assumptions on page 8, the F1 score proved completely inadequate for edge cases.")
        else:
            c.drawString(100, 750, f"This is placeholder text for page {i}.")
        c.showPage()
    c.save()

def run_eval(args):
    # --- Boundary Constraints Tests Commented Out ---
    # We removed the artificial limits in main.py to allow massive real research papers.
    # We don't need to test dummy 50MB and 500-page files anymore (and parsing 500 dummy pages takes 10 mins).
    print("--- 1. Boundary Constraints Test ---")
    print("SKIPPED: Artificial limits removed to allow real papers.")

    print("\n--- 2. End-to-End LLM Citation Evaluation ---")
    
    docs_to_test = []
    
    # Document A (Synthetic)
    if args.pdf_a == "generated":
        synth_pdf = "test_eval_synth.pdf"
        generate_synthetic_pdf(synth_pdf)
        docs_to_test.append(("Document A (Synthetic 54-page)", synth_pdf))
        
    # Document B (Real)
    real_pdf_path = args.real_pdf or args.pdf_b
    if real_pdf_path:
        if os.path.exists(real_pdf_path):
            docs_to_test.append(("Document B (Real PDF)", real_pdf_path))
        else:
            print(f"WARNING: Specified real PDF '{real_pdf_path}' not found.")
    
    if not docs_to_test:
        print("No documents to test. Exiting.")
        return

    questions = [
        # Factual
        "What is the name of the seminal paper mentioned?",
        "What was fundamentally changed by the paper?",
        # Semantic
        "Describe the core innovation of the proposed architecture.",
        "What are the structural components of the transformer?",
        # Cross-page synthesis (p12-13)
        "Summarize the events from page 12 to page 13.",
        # Explicit Multi-page disjoint synthesis (p8 and p37)
        "What was the primary evaluation metric and how did it perform for edge cases?",
        # Paraphrase
        "Who bankrolled the scientists' research efforts?",
        # Multi-page explicit
        "What paper proposed the breakthrough transformer architecture?",
        # Hard Refusal
        "What was the authors' total funding in 2024?",
        # Easy Refusal
        "What is the capital of France?"
    ]
    
    for doc_name, pdf_path in docs_to_test:
        print(f"\n--- Testing {doc_name} ---")
        doc_id = upload_pdf(pdf_path)
        if not doc_id:
            continue
            
        print("\nQ\tRetrieval\tAnswer\tHighlight\tRefusal")
        
        for i, q in enumerate(questions):
            ans, cites, elapsed, scores_data = run_query(doc_id, q)
            if ans is None:
                continue
                
            print(f"\nQ{i+1}: {q}")
            
            if scores_data and "scores" in scores_data:
                scores_list = [s["score"] for s in scores_data["scores"]]
                threshold = scores_data.get("threshold", 0.3)
                best_score = scores_list[0] if len(scores_list) > 0 else 0
                second_best = scores_list[1] if len(scores_list) > 1 else 0
                status = "accepted" if best_score >= threshold else "rejected"
                print(f"Retrieval Scores -> best_score: {best_score:.3f}, second_best_score: {second_best:.3f}, threshold: {threshold}, status: {status}")
            
            print(f"Answer ({elapsed:.2f}s): {ans}")
            print(f"Citations mapped: {len(cites)}")
            for c in cites:
                pages = list(set(w['page'] for w in c['words']))
                print(f"  - Citation spans pages: {pages} (Words: {len(c['words'])})")
                
        print(f"\n--- Evaluation Metrics Template for {doc_name} ---")
        print("Retrieval accuracy: _ / answerable questions")
        print("Highlight accuracy: _ / questions requiring citations")
        print("Answer accuracy: _ / answerable questions")
        print("Refusal accuracy: _ / total unsupported questions")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate PDF Q&A Engine")
    parser.add_argument("--pdf-a", type=str, default="generated", help="Path to Document A or 'generated'")
    parser.add_argument("--pdf-b", type=str, default=None, help="Path to Document B (real world PDF)")
    parser.add_argument("--real-pdf", type=str, default=None, help="Alias for --pdf-b")
    args = parser.parse_args()
    run_eval(args)
