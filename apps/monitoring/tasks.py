from celery import shared_task
from django.utils import timezone
from django.db.models import Avg, Max, Sum, Count
from apps.monitoring.models import Container, ContainerMetric, HourlyContainerMetric, MonthlyContainerMetric
import docker
import psutil
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import timedelta

logger = logging.getLogger(__name__)

def calculate_cpu_percent(d):
    cpu_count = len(d["cpu_stats"]["cpu_usage"]["percpu_usage"]) if "percpu_usage" in d["cpu_stats"]["cpu_usage"] else d["cpu_stats"].get("online_cpus", 1)
    cpu_percent = 0.0
    cpu_delta = float(d["cpu_stats"]["cpu_usage"]["total_usage"]) - \
                float(d["precpu_stats"]["cpu_usage"]["total_usage"])
    system_delta = float(d["cpu_stats"].get("system_cpu_usage", 0)) - \
                   float(d["precpu_stats"].get("system_cpu_usage", 0))
    if system_delta > 0.0:
        cpu_percent = cpu_delta / system_delta * 100.0 * cpu_count
    return round(cpu_percent, 2)

@shared_task
def collect_all_containers_metrics():
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
        channel_layer = get_channel_layer()
        
        # Broadcast Global Server Stats
        try:
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=None)
            async_to_sync(channel_layer.group_send)(
                "server_metrics_group",
                {
                    "type": "metrics_update",
                    "data": {
                        "cpu_percent": cpu,
                        "ram_total_mb": round(mem.total / (1024 * 1024), 2),
                        "ram_used_mb": round(mem.used / (1024 * 1024), 2),
                        "ram_percent": mem.percent
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error reading host stats: {e}")

        sub_metrics = {}
        
        for c in containers:
            try:
                project_name = c.labels.get('com.docker.compose.project', 'standalone')
                
                # Upsert container record
                container_obj, created = Container.objects.get_or_create(
                    container_id=c.id,
                    defaults={'name': c.name, 'status': c.status, 'project_name': project_name}
                )
                
                # Update status if it changed
                if not created and (container_obj.status != c.status or container_obj.project_name != project_name):
                    container_obj.status = c.status
                    container_obj.project_name = project_name
                    container_obj.save()
                
                # Only get stats if running
                if c.status == 'running':
                    stats = c.stats(stream=False)
                    
                    # CPU
                    cpu_percent = calculate_cpu_percent(stats)
                    
                    # Memory
                    mem_usage = stats.get('memory_stats', {}).get('usage', 0)
                    mem_limit = stats.get('memory_stats', {}).get('limit', 1)
                    
                    ram_mb = mem_usage / (1024 * 1024)
                    ram_percent = (mem_usage / mem_limit) * 100.0
                    
                    ContainerMetric.objects.create(
                        container=container_obj,
                        cpu_percent=cpu_percent,
                        ram_mb=round(ram_mb, 2),
                        ram_percent=round(ram_percent, 2)
                    )
                    
                    # Accumulate for WebSocket broadcast
                    if container_obj.subscription_id:
                        sub_id = container_obj.subscription_id
                        if sub_id not in sub_metrics:
                            sub_metrics[sub_id] = []
                        sub_metrics[sub_id].append({
                            'container_name': container_obj.name,
                            'cpu_percent': cpu_percent,
                            'ram_mb': round(ram_mb, 2)
                        })
            except Exception as ce:
                logger.error(f"Error processing container {c.name}: {ce}")
                    
        # Broadcast Subscription Metrics
        for sub_id, containers_data in sub_metrics.items():
            async_to_sync(channel_layer.group_send)(
                f"sub_metrics_{sub_id}",
                {
                    "type": "metrics_update",
                    "data": containers_data
                }
            )
                
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")

@shared_task
def aggregate_hourly_metrics():
    """
    Runs every hour to aggregate metrics from the previous hour.
    """
    now = timezone.now()
    last_hour = now - timedelta(hours=1)
    start_time = last_hour.replace(minute=0, second=0, microsecond=0)
    end_time = now.replace(minute=0, second=0, microsecond=0)
    
    containers = Container.objects.all()
    
    for container in containers:
        metrics = ContainerMetric.objects.filter(
            container=container,
            timestamp__range=(start_time, end_time)
        )
        
        if metrics.exists():
            summary = metrics.aggregate(
                avg_cpu=Avg('cpu_percent'),
                avg_ram=Avg('ram_mb'),
                max_cpu=Max('cpu_percent'),
                max_ram=Max('ram_mb')
            )
            
            HourlyContainerMetric.objects.update_or_create(
                container=container,
                timestamp=start_time,
                defaults={
                    'avg_cpu_percent': round(summary['avg_cpu'], 2),
                    'avg_ram_mb': round(summary['avg_ram'], 2),
                    'max_cpu_percent': round(summary['max_cpu'], 2),
                    'max_ram_mb': round(summary['max_ram'], 2),
                }
            )
            
            # Optionally clean up old raw metrics
            # ContainerMetric.objects.filter(timestamp__lt=now - timedelta(days=7)).delete()

@shared_task
def aggregate_monthly_metrics():
    """
    Runs daily to aggregate hourly metrics into monthly summaries.
    """
    now = timezone.now()
    # Aggregate for the current month so far
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    containers = Container.objects.all()
    
    for container in containers:
        hourly_metrics = HourlyContainerMetric.objects.filter(
            container=container,
            timestamp__gte=start_of_month
        )
        
        if hourly_metrics.exists():
            summary = hourly_metrics.aggregate(
                avg_cpu=Avg('avg_cpu_percent'),
                avg_ram=Avg('avg_ram_mb'),
                count=Count('id')
            )
            
            # GB-Hours calculation: (Avg RAM in MB / 1024) * Hours
            gb_hours = (summary['avg_ram'] / 1024.0) * summary['count']
            
            MonthlyContainerMetric.objects.update_or_create(
                container=container,
                timestamp=start_of_month,
                defaults={
                    'avg_cpu_percent': round(summary['avg_cpu'], 2),
                    'avg_ram_mb': round(summary['avg_ram'], 2),
                    'total_gb_hours': round(gb_hours, 4)
                }
            )
