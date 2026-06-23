import google.generativeai as genai

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL
)

genai.configure(
    api_key=GEMINI_API_KEY
)


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

        model = genai.GenerativeModel(
            GEMINI_MODEL
        )

        response = model.generate_content(
            prompt
        )

        answer = response.text

        if not answer:
            return "Answer not found in uploaded documents."

        return answer.strip()

    except Exception as e:

        print("Gemini Error:", e)

        return "Answer not found in uploaded documents."