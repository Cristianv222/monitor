import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('docker_monitor')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'collect-metrics-every-5-seconds': {
        'task': 'apps.monitoring.tasks.collect_all_containers_metrics',
        'schedule': 5.0,
    },
    'check-alerts-every-minute': {
        'task': 'apps.alerts.tasks.check_all_alerts',
        'schedule': 60.0,
    },
    'cleanup-old-metrics-daily': {
        'task': 'apps.monitoring.tasks.cleanup_old_metrics',
        'schedule': crontab(hour=2, minute=0),
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
