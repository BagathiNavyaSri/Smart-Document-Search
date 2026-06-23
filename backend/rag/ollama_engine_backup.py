import requests

from config import OLLAMA_MODEL


# =========================================
# GENERATE AI RESPONSE
# =========================================

def generate_ai_response(
    query,
    retrieved_chunks
):

    if not retrieved_chunks:

        return "No relevant information found."

    context = "\n\n".join(
        [item["chunk"] for item in retrieved_chunks]
    )

    prompt = f"""
You are an intelligent AI document assistant.

Answer ONLY using the provided context.

Rules:
- Give clean, structured answers.
- Use bullet points when needed.
- Keep answers concise but informative.
- Do not hallucinate.
- If answer is unavailable, say:
"Answer not found in uploaded documents."

Context:
{context}

Question:
{query}

Answer:
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        answer = result.get("response")
        if not answer:
            return "Answer not found in uploaded documents."
        return answer.strip()
    except requests.RequestException:
        return "Answer not found in uploaded documents."