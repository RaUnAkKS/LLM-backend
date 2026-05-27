import faiss
import numpy as np
import os
import json

# in-memory store
faiss_indexes = {}   # {document_id: index}
chunk_text_map = {}  # {document_id: [chunk_texts]}

def get_index_path(document_id):
    os.makedirs("faiss_indexes", exist_ok=True)
    return os.path.join("faiss_indexes", f"faiss_{document_id}.index")

def get_map_path(document_id):
    os.makedirs("faiss_indexes", exist_ok=True)
    return os.path.join("faiss_indexes", f"faiss_{document_id}_map.json")

def create_faiss_index(document_id, chunks):
    """
    chunks = list of (text, embedding)
    """

    embeddings = np.array([c[1] for c in chunks]).astype("float32")

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    # store in memory
    faiss_indexes[document_id] = index
    text_list = [c[0] for c in chunks]
    chunk_text_map[document_id] = text_list

    # save to disk
    faiss.write_index(index, get_index_path(document_id))
    with open(get_map_path(document_id), "w", encoding="utf-8") as f:
        json.dump(text_list, f)

def search_faiss(document_id, query_embedding, k=3):
    index = faiss_indexes.get(document_id)

    # Try loading from disk if not in memory
    if index is None:
        index_path = get_index_path(document_id)
        map_path = get_map_path(document_id)
        if os.path.exists(index_path) and os.path.exists(map_path):
            index = faiss.read_index(index_path)
            with open(map_path, "r", encoding="utf-8") as f:
                chunk_text_map[document_id] = json.load(f)
            faiss_indexes[document_id] = index
        else:
            return []

    query_vector = np.array([query_embedding]).astype("float32")

    distances, indices = index.search(query_vector, k)

    results = []
    for i in indices[0]:
        # -1 means not found (e.g., if there are fewer chunks than k)
        if i != -1 and i < len(chunk_text_map[document_id]):
            results.append(chunk_text_map[document_id][i])

    return results