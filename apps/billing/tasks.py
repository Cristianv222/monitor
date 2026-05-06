from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from apps.billing.models import Subscription
from apps.alerts.models import Alert
import requests
import datetime
import docker

def calculate_days_difference(cutoff_day):
    today = timezone.now().date()
    # Try to construct cutoff date for this month
    try:
        cutoff_date = datetime.date(today.year, today.month, cutoff_day)
    except ValueError:
        # e.g., February 30th -> fallback to last day of month
        # Simplification for demo: just use 28
        cutoff_date = datetime.date(today.year, today.month, 28)
        
    diff = (cutoff_date - today).days
    return diff

def send_email_alert(client, days_left):
    if not client.email:
        return
        
    subject = f"Aviso de Facturación: {days_left} días para el corte"
    message = f"Hola {client.name},\n\nEste es un recordatorio automático de que tu suscripción vence en {days_left} días.\nPor favor realiza el pago para evitar la suspensión de tus contenedores.\n\nSaludos,\nEl equipo de Monitorización"
    
    try:
        send_mail(
            subject,
            message,
            'billing@monitor.local',
            [client.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Email failed for {client.name}: {e}")

@shared_task
def process_billing_cycles():
    subscriptions = Subscription.objects.filter(status='active')
    docker_client = docker.from_env()
    
    for sub in subscriptions:
        diff = calculate_days_difference(sub.cutoff_day)
        
        # Reminders at 5 and 3 days before cutoff
        if diff == 5 or diff == 3:
            # Send Email
            send_email_alert(sub.client, diff)
            # Create internal Alert
            Alert.objects.create(
                message=f"Recordatorio de pago enviado a {sub.client.name} ({diff} días)",
                severity='info'
            )
            
        # Penalty: 2 days AFTER cutoff (diff <= -2)
        elif diff <= -2:
            sub.status = 'suspended'
            sub.save()
            
            # Stop all associated containers
            containers = sub.containers.all()
            for c_model in containers:
                try:
                    container = docker_client.containers.get(c_model.container_id)
                    container.stop()
                    Alert.objects.create(
                        message=f"Contenedor {c_model.name} SUSPENDIDO por falta de pago (Cliente: {sub.client.name})",
                        severity='critical'
                    )
                except Exception as e:
                    print(f"Failed to stop container {c_model.container_id}: {e}")
                    
            # Notify suspension
            send_email_alert(sub.client, diff)
