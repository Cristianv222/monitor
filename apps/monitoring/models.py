from django.db import models

class Container(models.Model):
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('exited', 'Exited'),
        ('paused', 'Paused'),
        ('created', 'Created'),
    ]
    
    container_id = models.CharField(max_length=100, unique=True, verbose_name="Container ID")
    name = models.CharField(max_length=255, verbose_name="Name")
    project_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Project Name")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', verbose_name="Status")
    subscription = models.ForeignKey('billing.Subscription', on_delete=models.SET_NULL, null=True, blank=True, related_name='containers')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    
    def __str__(self):
        return f"{self.name} ({self.container_id[:12]})"

    class Meta:
        verbose_name = "Container"
        verbose_name_plural = "Containers"
        ordering = ['-created_at']

class ContainerMetric(models.Model):
    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name='metrics')
    cpu_percent = models.FloatField(default=0.0)
    ram_mb = models.FloatField(default=0.0)
    ram_percent = models.FloatField(default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['container', '-timestamp']),
        ]
