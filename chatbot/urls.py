from django.urls import path
from .views import AskAPIView, ChatSessionListAPIView, DocumentUploadAPIView, TaskStatusAPIView, SessionMessagesAPIView, CancelTaskAPIView

urlpatterns = [
    path("ask/", AskAPIView.as_view(), name="ask"),
    path("sessions/", ChatSessionListAPIView.as_view(), name="sessions"),
    path("sessions/<int:session_id>/messages/", SessionMessagesAPIView.as_view(), name="session-messages"),
    path("upload/", DocumentUploadAPIView.as_view(), name="upload"),
    path("task-status/<str:task_id>/", TaskStatusAPIView.as_view(), name="task-status"),
    path("cancel-task/<str:task_id>/", CancelTaskAPIView.as_view(), name="cancel-task"),
]