import asyncio
import httpx
import time
from pathlib import Path

async def test_upload(client, test_pdf_path):
    with open(test_pdf_path, 'rb') as f:
        files = {'file': ('test.pdf', f, 'application/pdf')}
        try:
            r = await client.post('http://localhost:8000/upload', files=files)
            if r.status_code == 200:
                return r.json()['doc_id']
        except Exception as e:
            print(f"Upload failed: {e}")
    return None

async def test_qa(client, doc_id):
    try:
        r = await client.get(f'http://localhost:8000/query?doc_id={doc_id}&q=What is this?')
        # The endpoint streams, so we just read the response
        async for _ in r.aiter_lines():
            pass
        return True
    except Exception as e:
        print(f"QA failed: {e}")
        return False

async def stress_worker(worker_id, test_pdf_path):
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Simulate an upload
        doc_id = await test_upload(client, test_pdf_path)
        if doc_id:
            # Simulate QA
            await test_qa(client, doc_id)
            print(f"Worker {worker_id} completed successfully.")
        else:
            print(f"Worker {worker_id} failed to upload.")

async def main():
    print("Starting Project 1 Stress Test...")
    test_pdf_path = Path("samples/sample_input.pdf")
    if not test_pdf_path.exists():
        # Create a dummy PDF if sample_input.pdf doesn't exist
        print(f"Sample PDF not found at {test_pdf_path}. Cannot stress test.")
        return
    
    # Launch 50 concurrent requests
    start_time = time.time()
    tasks = [stress_worker(i, test_pdf_path) for i in range(50)]
    await asyncio.gather(*tasks)
    end_time = time.time()
    print(f"Stress test completed in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    asyncio.run(main())
