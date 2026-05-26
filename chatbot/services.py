import json
from groq import Groq
from django.conf import settings
from django.core.cache import cache
import hashlib
from .embeddings import get_top_k_chunks
client = Groq(api_key=settings.GROQ_API_KEY)

def build_messages(system_prompt, history, user_question, document_id=None):
    messages = [{"role": "system", "content": system_prompt}]
    
    if document_id:
        query_type = classify_query(user_question)
        if query_type == "specific":
            chunks = get_top_k_chunks(user_question, document_id, k=3)
            context = "\n\n".join(chunks)
        else:
            diverse = get_diverse_chunks(document_id, k=6)
            relevant = get_top_k_chunks(user_question, document_id, k=2)
            context = "\n\n".join(diverse + relevant)
        system_prompt = """
        You are an AI assistant.

        Use the provided {context} to answer.

        If the {user_question} is global:
        - Give a structured summary
        - Cover all major sections

        If the {user_question} is specific:
        - Answer precisely

        Return JSON:
        {
        "explanation": "...",
        "example": "...",
        "key_points": ["..."]
        }
        """
        messages.append({
            "role": "system",
            "content": f"Use this document to answer:\n{context}"
        })
    for msg in history:
        messages.append({
            "role": msg.role,
            "content": msg.content
        })

    messages.append({"role": "user", "content": user_question})

    return messages


def ask_llm(question: str, history, tone: str, document_id: int = None) -> str:
    """
    Sends question to Groq LLM and returns response
    """
    tone = tone.strip().lower()
    if tone == "student":
        system_prompt = """
        You are a helpful AI tutor for students.

        Answer ONLY using the provided context.

        If answer is not in context, say:
        "I don't know based on the document."

        Return response strictly in JSON format:

        {
          "explanation": "...",
          "example": "...",
          "key_points": ["...", "..."]
        }

        Rules:
        - Keep it simple
        - Be accurate to document
        - Do NOT add anything outside JSON
        """

    elif tone == "teacher":
        system_prompt = """
        You are an expert teacher.

        Answer ONLY using the provided context.

        If answer is not in context, say:
        "I don't know based on the document."

        Return response strictly in JSON format:

        {
          "explanation": "...",
          "example": "...",
          "key_points": ["...", "..."]
        }

        Rules:
        - Be precise and structured
        - Do NOT add anything outside JSON
        """
    elif tone == "quiz":
        system_prompt = """
        You are an expert teacher.

        Answer ONLY using the provided context.

        If answer is not in context, say:
        "I don't know based on the document."

        Return response strictly in JSON format:

        {
        "summary": "...",
        "quiz": [
            {
            "question": "...",
            "options": ["A", "B", "C", "D"],
            "answer": "..."
            }
        ]
        }

        Rules:
        - Be precise and structured
        - Do NOT add anything outside JSON
        """
    else:
        system_prompt = """You are a helpful AI assistant."
        Answer ONLY using the provided context.

        If answer is not in context, say:
        "I don't know based on the document."

        Return response strictly in JSON format:

        {
          "response": "..."
        }
        """
    messages = build_messages(system_prompt, history, question, document_id)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.5,
        timeout=10
    )

    return response.choices[0].message.content

def classify_query(question: str):
    # Generate a cache key based on the question
    cache_key = f"classify_query_{hashlib.md5(question.encode('utf-8')).hexdigest()}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    prompt = f"""
    Classify the user query into one of these types:

    1. specific → asking about a specific concept
    2. global → asking about entire document (summary, overview)

    Return ONLY one word: specific or global

    Query: {question}
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    result = response.choices[0].message.content.strip().lower()
    cache.set(cache_key, result, timeout=86400) # Cache for 24 hours
    return result