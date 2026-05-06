from django.db import models

class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]
    
    message = models.TextField(verbose_name="Alert Message")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='info', verbose_name="Severity")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    is_resolved = models.BooleanField(default=False, verbose_name="Is Resolved")
    triggered_at = models.DateTimeField(auto_now_add=True, verbose_name="Triggered At")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Resolved At")
    
    def __str__(self):
        return f"[{self.get_severity_display()}] {self.message[:50]}"

    class Meta:
        verbose_name = "Alert"
        verbose_name_plural = "Alerts"
        ordering = ['-triggered_at']
