import httpx
import json
import asyncio
import re

SYSTEM_PROMPT = """You are a precise document Q&A assistant. Answer ONLY from the provided context passages.

Rules:
1. Every factual claim must cite its source by quoting the exact supporting sentence using XML tags: <cite doc="S1">exact quote here</cite>.
   Example: The sky is blue <cite doc="S1">The sky appears blue due to Rayleigh scattering.</cite>.
2. If the answer spans multiple passages, cite each one.
3. If the document does not contain the answer, say exactly:
   "The document does not contain enough information to answer this question."
   Do NOT guess or hallucinate.
4. Be concise. Do not pad with filler text.
"""

CONTEXT = """[Document S1]
The Apollo 11 mission was the first manned mission to land on the Moon. It was launched by a Saturn V rocket from Kennedy Space Center on July 16, 1969.

[Document S2]
Commander Neil Armstrong and lunar module pilot Buzz Aldrin formed the American crew that landed the Apollo Lunar Module Eagle on July 20, 1969, at 20:17 UTC.

[Document S3]
Armstrong became the first person to step onto the lunar surface six hours and 39 minutes later on July 21 at 02:56 UTC; Aldrin joined him 19 minutes later.
"""

QUESTIONS = [
    "Who was the first person to step on the Moon?",
    "When did Apollo 11 launch?",
    "What rocket was used for Apollo 11?",
    "Who was the lunar module pilot?",
    "What time did they land on the moon?",
    "When did Aldrin join Armstrong on the surface?",
    "Where did the rocket launch from?",
    "What was the name of the lunar module?",
    "Who was the commander of the mission?",
    "How many hours after landing did Armstrong step on the moon?",
    "What is the airspeed velocity of an unladen swallow?", # should be refusal
    "How many people walked on the moon during Apollo 11?",
    "What day did Armstrong step on the moon?",
    "What vehicle launched them?",
    "What time did Armstrong step on the moon?",
    "Did Buzz Aldrin step on the moon?",
    "How many minutes later did Aldrin join Armstrong?",
    "What year did they land on the moon?",
    "What UTC time did the Eagle land?",
    "Where did the Saturn V launch from?",
]

async def run_test():
    ollama_url = "http://localhost:11434/api/generate"
    
    success_count = 0
    refusal_count = 0
    malformed_count = 0

    print("Running Llama 3.1 Tag Format Test...\n")

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, q in enumerate(QUESTIONS):
            prompt = f"{SYSTEM_PROMPT}\n\nContext passages:\n\n{CONTEXT}\n\nQuestion: {q}"
            payload = {
                "model": "llama3.1",
                "prompt": prompt,
                "stream": False,
            }
            
            try:
                resp = await client.post(ollama_url, json=payload)
                if resp.status_code != 200:
                    print(f"[{i+1}/20] Failed to connect to Ollama.")
                    continue
                
                answer = resp.json().get("response", "")
                
                # Check for refusal
                if "does not contain enough information" in answer:
                    print(f"[{i+1}/20] Refusal (Correct) - Q: {q}")
                    refusal_count += 1
                    continue
                
                # Check for well-formed tags
                tags = re.findall(r'<cite doc="S\d+">.*?</cite>', answer)
                open_tags = re.findall(r'<cite', answer)
                
                if len(tags) > 0 and len(tags) == len(open_tags):
                    print(f"[{i+1}/20] Success - Q: {q} | Citations: {len(tags)}")
                    success_count += 1
                else:
                    print(f"[{i+1}/20] MALFORMED - Q: {q} | Answer: {answer}")
                    malformed_count += 1
                    
            except Exception as e:
                print(f"[{i+1}/20] Error: {e}")
                
    print("\n--- RESULTS ---")
    print(f"Total Questions: 20")
    print(f"Success (Well-formed tags): {success_count}")
    print(f"Refusals: {refusal_count}")
    print(f"Malformed tags: {malformed_count}")

if __name__ == "__main__":
    asyncio.run(run_test())
