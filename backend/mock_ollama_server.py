import asyncio
import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()

MOCK_RESPONSES = {
    "default": [
        "The", " study", " found", " a", " significant", " improvement", ".\n",
        "<cite doc=\"S1\">", "this text does not exist in any chunk anywhere", "</cite>", " ",
        "This", " is", " verified", " by", " the", " authors", "."
    ]
}

@app.post("/api/generate")
async def generate(request: Request):
    body = await request.json()
    
    async def generate_response():
        # Yield deterministic tokens
        tokens = MOCK_RESPONSES.get("default")
        for t in tokens:
            chunk = {
                "model": body.get("model", "llama3.1"),
                "response": t,
                "done": False
            }
            yield json.dumps(chunk) + "\n"
            await asyncio.sleep(0.05)
            
        final_chunk = {
            "model": body.get("model", "llama3.1"),
            "response": "",
            "done": True
        }
        yield json.dumps(final_chunk) + "\n"

    return StreamingResponse(generate_response(), media_type="application/x-ndjson")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=11434)
