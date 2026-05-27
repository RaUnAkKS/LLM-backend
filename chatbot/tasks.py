from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded  # ← for graceful timeout handling
from .models import Document, DocumentChunk
from .utils import extract_text_from_file
from .embeddings import chunk_text, get_embedding
from .faiss_index import create_faiss_index
import time

@shared_task(
    bind=True,
    queue='celery',   # ← explicitly route to 'celery' worker
    soft_time_limit=60,   # at 60s → raises SoftTimeLimitExceeded (catchable ✅)
    time_limit=90         # at 90s → hard kill, no cleanup possible ❌
)
def process_document(self, document_id):
    """
    Background task: extract text → chunk → embed → index
    Runs AFTER the upload view returns instantly.
    - soft_time_limit: gives us a chance to clean up at 60s
    - time_limit: nuclear option at 90s if task is completely stuck
    """
    document = None  # declare outside try so except blocks can access it
    try:
        document = Document.objects.get(id=document_id)
        document.status = "processing"
        document.save()

        # Step A: Text already extracted at upload time
        text = document.extracted_text

        # Step B: Chunk the text
        chunks = chunk_text(text)

        # Clear any existing chunks (e.g. from a previous failed attempt)
        DocumentChunk.objects.filter(document=document).delete()

        # Step C: Embed each chunk + save to DB
        chunks_data = []
        for i, chunk in enumerate(chunks):
            self.update_state(
                state='PROGRESS',
                meta={'current': i, 'total': len(chunks), 'step': 'embedding'}
            )
            embedding = get_embedding(chunk)
            DocumentChunk.objects.create(
                document=document,
                text=chunk,
                embedding=embedding
            )
            chunks_data.append((chunk, embedding))
            time.sleep(0.1)  # respect API rate limits

        # Step D: Build FAISS index
        create_faiss_index(document.id, chunks_data)

        document.status = "ready"
        document.save()
        return {"status": "success", "document_id": document_id}

    except SoftTimeLimitExceeded:
        # ← triggered at exactly 60 seconds
        # We get a chance to clean up gracefully before hard kill at 90s
        if document:
            document.status = "failed"
            document.save()
        # Do NOT retry on timeout — the task will just timeout again
        raise  # re-raise so Celery marks it as FAILURE

    except Exception as e:
        # All other errors (API error, DB error, etc.)
        if document:
            document.status = "failed"
            document.save()
        raise self.retry(exc=e, countdown=5, max_retries=3)
