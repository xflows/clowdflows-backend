

import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mothra.settings')

app = Celery('mothra')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(settings.INSTALLED_APPS, related_name='tasks')

app.conf.CELERYBEAT_SCHEDULE = {
    'update-recommendations': {
        'task': 'workflows.tasks.updateRecommendations',
        'schedule': crontab(minute=0, hour=0)  # Executes daily at midnight
    },
}

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
