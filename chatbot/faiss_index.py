import faiss
import numpy as np

# in-memory store (for now)
faiss_indexes = {}   # {document_id: index}
chunk_text_map = {}  # {document_id: [chunk_texts]}


def create_faiss_index(document_id, chunks):
    """
    chunks = list of (text, embedding)
    """

    embeddings = np.array([c[1] for c in chunks]).astype("float32")

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    # store
    faiss_indexes[document_id] = index
    chunk_text_map[document_id] = [c[0] for c in chunks]

def search_faiss(document_id, query_embedding, k=3):
    index = faiss_indexes.get(document_id)

    if index is None:
        return []

    query_vector = np.array([query_embedding]).astype("float32")

    distances, indices = index.search(query_vector, k)

    results = []
    for i in indices[0]:
        results.append(chunk_text_map[document_id][i])

    return results