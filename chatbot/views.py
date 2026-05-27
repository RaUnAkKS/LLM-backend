from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import AskSerializer
from .services import ask_llm
from .models import ChatSession, Message , Document,DocumentChunk
import json
from .utils import extract_text_from_file
from .embeddings import chunk_text, get_embedding
from .faiss_index import create_faiss_index, search_faiss
from .tasks import process_document
from celery.result import AsyncResult

class AskAPIView(APIView):

    def post(self, request):
        serializer = AskSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        question = serializer.validated_data["question"]
        tone = serializer.validated_data.get("tone")
        session_id = serializer.validated_data.get("session_id")
        document_id = serializer.validated_data.get("document_id")

        document_text = None
        if document_id:
            document = Document.objects.get(id=document_id)
            document_text = document.extracted_text
        if session_id:
            session = ChatSession.objects.get(id=session_id)
        else:
            session = ChatSession.objects.create(title=question[:50])

        Message.objects.create(
            session=session,
            role="user",
            content=question
        )
        history = Message.objects.filter(session=session).order_by("created_at")
        try:
            response_text = ask_llm(question, history, tone, document_id)
            
            try:
                ai_response = json.loads(response_text)
            except:
                ai_response = {"raw": response_text}

            Message.objects.create(
                session=session,
                role="assistant",
                content=response_text
            )

            return Response({
                "session_id": session.id,
                "answer": ai_response
            })  
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Error in AskAPIView")
            
            err_msg = str(e)
            if "getaddrinfo failed" in err_msg or "Connection error" in err_msg or "ConnectError" in err_msg:
                friendly_msg = "Connection to the Groq AI service failed. Please check your internet connection, proxy, or VPN settings."
            else:
                friendly_msg = f"Failed to get AI response: {err_msg}"
                
            return Response({"error": friendly_msg}, status=status.HTTP_502_BAD_GATEWAY)
    
class ChatSessionListAPIView(APIView):
    def get(self, request):
        sessions = ChatSession.objects.all().order_by("-created_at")
        data = []
        for session in sessions:
            data.append({
                    "id": session.id,
                    "title": session.title,
                    "created_at": session.created_at
                })
        return Response(data)

class SessionMessagesAPIView(APIView):
    def get(self, request, session_id):
        try:
            session = ChatSession.objects.get(id=session_id)
            messages = Message.objects.filter(session=session).order_by("created_at")
            data = []
            for msg in messages:
                data.append({
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at
                })
            return Response(data)
        except ChatSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)

class DocumentUploadAPIView(APIView):

    def post(self, request):
        file = request.FILES.get("file")

        if not file:
            return Response({"error": "No file provided"}, status=400)

        # Validate file size (10MB limit)
        if file.size > 10 * 1024 * 1024:
            return Response({"error": "File size must be less than 10MB"}, status=400)

        # Validate extension
        ext = file.name.split('.')[-1].lower()
        if ext not in ['pdf', 'docx', 'txt']:
            return Response({"error": "Only PDF, DOCX, and TXT files are allowed"}, status=400)

        try:
            text = extract_text_from_file(file)
            # chunks = chunk_text(text)
            document = Document.objects.create(
                file=file,
                extracted_text=text,
                status="pending"
            )
            task=process_document.delay(document.id)
            # chunks_data = []
            # for chunk in chunks:
            #     embedding = get_embedding(chunk)
            #     DocumentChunk.objects.create(
            #         document=document,
            #         text=chunk,
            #         embedding=embedding
            #     )
            #     chunks_data.append((chunk, embedding))
            
            # create_faiss_index(document.id, chunks_data)
            # return Response({
            #     "document_id": document.id,
            #     "message": "Uploaded successfully"
            # })

            # Step 4: Return IMMEDIATELY — don't wait!
            return Response({
                "document_id": document.id,
                "task_id": task.id,
                "status": "processing",
                "message": "File uploaded. Processing in background..."
            }, status=202)  # 202 Accepted

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class TaskStatusAPIView(APIView):
    """
    GET /task-status/<task_id>/
    Frontend polls this to check if document processing is done.
    """
    def get(self, request, task_id):
        result = AsyncResult(task_id)

        if result.state == 'PENDING':
            response = {
                "status": "pending",
                "message": "Task is waiting in queue...",
                "progress": 0
            }
        elif result.state == 'PROGRESS':
            info = result.info or {}
            current = info.get('current', 0)
            total = info.get('total', 1)
            response = {
                "status": "processing",
                "step": info.get('step', 'working'),
                "current": current,
                "total": total,
                "progress": int((current / total) * 100)
            }
        elif result.state == 'SUCCESS':
            response = {
                "status": "ready",
                "message": "Document is ready to chat!",
                "progress": 100,
                "result": result.result
            }
        else:  # FAILURE
            response = {
                "status": "failed",
                "message": "Processing failed. Please re-upload.",
                "error": str(result.info)
            }

        return Response(response)

class CancelTaskAPIView(APIView):
    def delete(self, request, task_id):
        AsyncResult(task_id).revoke(terminate=True)
        return Response({"message": "Task cancelled"})