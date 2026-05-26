from .models import DocumentChunk
from django.core.cache import cache
import hashlib
def chunk_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


from sentence_transformers import SentenceTransformer

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def get_embedding(text):
    cache_key = f"embedding_{hashlib.md5(text.encode('utf-8')).hexdigest()}"
    cached_emb = cache.get(cache_key)
    if cached_emb:
        return cached_emb

    emb = _get_model().encode(text).tolist()
    cache.set(cache_key, emb, timeout=86400 * 7) # Cache for 7 days
    return emb

import numpy as np


def cosine_similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    return np.dot(vec1, vec2) / (
        np.linalg.norm(vec1) * np.linalg.norm(vec2)
    )# cos angle between two vectors
    #dot_product / (magnitude1 * magnitude2)
    # if angle is 0 then vectors are same = 1
    # if angle is 90 then vectors are perpendicular = 0
    # if angle is 180 then vectors are opposite = -1

from .models import DocumentChunk
from .faiss_index import search_faiss

def get_top_k_chunks(question, document_id, k=3):
    query_embedding = get_embedding(question)

    # chunks = DocumentChunk.objects.filter(document_id=document_id)

    # scored_chunks = []

    # for chunk in chunks:
    #     score = cosine_similarity(query_embedding, chunk.embedding)
    #     scored_chunks.append((score, chunk.text))

    # scored_chunks.sort(reverse=True, key=lambda x: x[0])

    # top_chunks = [text for _, text in scored_chunks[:k]]

    # return top_chunks
    return search_faiss(document_id, query_embedding, k)

def get_diverse_chunks(document_id, k=8):
    cache_key = f"diverse_chunks_{document_id}_{k}"
    cached_chunks = cache.get(cache_key)
    if cached_chunks:
        return cached_chunks

    chunks = DocumentChunk.objects.filter(document_id=document_id)

    total = len(chunks)
    step = max(1, total // k)

    selected = []

    for i in range(0, total, step):
        selected.append(chunks[i].text)
        if len(selected) >= k:
            break

    cache.set(cache_key, selected, timeout=86400 * 7)
    return selected