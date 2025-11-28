import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_manager.settings')

app = Celery('finance_manager')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
