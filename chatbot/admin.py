from django.contrib import admin
from .models import ChatSession, Message, Document, DocumentChunk

admin.site.register(ChatSession)
admin.site.register(Message)
admin.site.register(Document)
admin.site.register(DocumentChunk)
