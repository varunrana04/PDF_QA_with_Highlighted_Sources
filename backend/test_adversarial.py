import httpx
import asyncio
import os

BASE_URL = "http://localhost:8001"

async def test_adversarial():
    print("--- Adversarial Testing for PDF Q&A Backend ---")
    async with httpx.AsyncClient() as client:
        # Test 1: Uploading a non-PDF file
        print("\nTest 1: Uploading a non-PDF file")
        files = {'file': ('test.txt', b"Hello World, this is not a PDF.", 'text/plain')}
        res = await client.post(f"{BASE_URL}/upload", files=files)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")

        # Test 2: Uploading an empty file
        print("\nTest 2: Uploading an empty file")
        files = {'file': ('empty.pdf', b"", 'application/pdf')}
        res = await client.post(f"{BASE_URL}/upload", files=files)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")

        # Test 3: Query with invalid doc_id
        print("\nTest 3: Query with invalid doc_id")
        res = await client.get(f"{BASE_URL}/query", params={"doc_id": "invalid-id", "question": "test", "api_key": "test"})
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")

        # Test 4: Query with empty question
        print("\nTest 4: Query with empty question")
        res = await client.get(f"{BASE_URL}/query", params={"doc_id": "invalid-id", "question": "", "api_key": "test"})
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")

if __name__ == "__main__":
    asyncio.run(test_adversarial())
