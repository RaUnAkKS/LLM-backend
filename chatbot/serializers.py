from rest_framework import serializers
from .models import Document

class AskSerializer(serializers.Serializer):
    question = serializers.CharField()
    tone = serializers.CharField(required=False,default="student")
    document_id = serializers.IntegerField(required=False)
    session_id = serializers.IntegerField(required=False)

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "file"]
    
    def validate_file(self,value):
        ext=value.name.split('.')[-1].lower()
        if ext not in ['pdf','txt','docx']:
            raise serializers.ValidationError("Only PDF, TXT, DOCX files are allowed")
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size must be less than 10MB")
        return value

