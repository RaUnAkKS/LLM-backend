import os
from celery import Celery

# Tell celery which Django settings to use
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LLM.settings')

app = Celery('LLM')

# Read config from Django settings, namespace 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps (finds chatbot/tasks.py)
app.autodiscover_tasks()
