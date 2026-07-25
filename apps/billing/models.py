from django.db import models
from django.utils import timezone
import uuid

class Client(models.Model):
    name = models.CharField(max_length=255, verbose_name="Razón Social / Nombre")
    cedula_ruc = models.CharField(max_length=20, unique=True, verbose_name="Cédula / RUC", default="0000000000")
    email = models.EmailField(verbose_name="Correo Electrónico")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Teléfono")
    address = models.TextField(blank=True, null=True, verbose_name="Dirección Física")
    
    # Auto-generated API Token
    api_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled')
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='subscriptions')
    plan_name = models.CharField(max_length=100, default='Standard Hosting')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monthly Price")
    
    # Billing cycle
    cutoff_day = models.IntegerField(verbose_name="Cutoff Day (1-31)", default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    last_paid_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.plan_name} - {self.client.name}"

class SystemSettings(models.Model):
    vps_monthly_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Costo Mensual del VPS ($)")
    total_server_ram_gb = models.FloatField(default=1.0, verbose_name="Memoria RAM Total del VPS (GB)")
    
    class Meta:
        verbose_name = "ConfiguraciÃ³n del Sistema"
        verbose_name_plural = "Configuraciones del Sistema"

    def __str__(self):
        return "ConfiguraciÃ³n Global"
