from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json

class Command(BaseCommand):
    help = 'Initializes the periodic tasks for resource monitoring and aggregation.'

    def handle(self, *args, **options):
        # 1. Metric Collection (Every 30 seconds)
        schedule_30s, _ = IntervalSchedule.objects.get_or_create(
            every=30,
            period=IntervalSchedule.SECONDS,
        )

        PeriodicTask.objects.get_or_create(
            interval=schedule_30s,
            name='Collect Container Metrics',
            task='apps.monitoring.tasks.collect_all_containers_metrics',
        )

        # 2. Hourly Aggregation (At minute 0 of every hour)
        schedule_hourly, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='*',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )

        PeriodicTask.objects.get_or_create(
            crontab=schedule_hourly,
            name='Aggregate Hourly Metrics',
            task='apps.monitoring.tasks.aggregate_hourly_metrics',
        )

        # 3. Monthly Aggregation (Daily at 01:00 AM)
        schedule_daily, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='1',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )

        PeriodicTask.objects.get_or_create(
            crontab=schedule_daily,
            name='Aggregate Monthly Metrics',
            task='apps.monitoring.tasks.aggregate_monthly_metrics',
        )

        self.stdout.write(self.style.SUCCESS('Successfully initialized periodic tasks.'))
