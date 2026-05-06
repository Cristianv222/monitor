from celery import shared_task
from django.utils import timezone
from apps.monitoring.models import Container, ContainerMetric
import docker
import psutil
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

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
            print(f"Error reading host stats: {e}")

        sub_metrics = {}
        
        for c in containers:
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
        print(f"Error collecting metrics: {e}")
