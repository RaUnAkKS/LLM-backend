from django.urls import path
from .views import AskAPIView, ChatSessionListAPIView, DocumentUploadAPIView, TaskStatusAPIView

urlpatterns = [
    path("ask/", AskAPIView.as_view(), name="ask"),
    path("sessions/", ChatSessionListAPIView.as_view(), name="sessions"),
    path("upload/", DocumentUploadAPIView.as_view(), name="upload"),
    path("task-status/<str:task_id>/", TaskStatusAPIView.as_view(), name="task-status"),
]