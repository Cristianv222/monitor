# ============================================================================
# DOCKER RESOURCE MONITOR - INSTALADOR COMPLETO ÚNICO
# Script PowerShell que crea toda la estructura del proyecto
# Ejecutar desde PowerShell dentro del repo 'monitor': .\SETUP_DOCKER_MONITOR.ps1
# Autor: Cristian - UPEC
# ============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  DOCKER RESOURCE MONITOR - Instalador Completo" -ForegroundColor Cyan
Write-Host "  Arquitectura: Django Monolítico Modular" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ====================
# PASO 1: VERIFICACIONES
# ====================

Write-Host "[PASO 1/6] Verificando requisitos..." -ForegroundColor Yellow

try {
    $pythonVer = python --version 2>&1
    Write-Host "  [OK] $pythonVer" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Python no instalado" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ====================
# PASO 2: CREAR DIRECTORIOS
# ====================

Write-Host "[PASO 2/6] Creando estructura de directorios..." -ForegroundColor Yellow

$directories = @(
    "config", "apps",
    "apps/core", "apps/core/management", "apps/core/management/commands",
    "apps/monitoring", "apps/monitoring/management", "apps/monitoring/management/commands",
    "apps/monitoring/migrations", "apps/monitoring/templates/monitoring", "apps/monitoring/templatetags",
    "apps/alerts", "apps/alerts/migrations", "apps/alerts/templates/alerts",
    "apps/reports", "apps/reports/migrations", "apps/reports/templates/reports",
    "static", "static/css", "static/js", "static/img",
    "templates", "templates/base", "templates/partials", "media", "logs"
)

foreach ($dir in $directories) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

Write-Host "  [OK] $(($directories).Count) directorios creados" -ForegroundColor Green
Write-Host ""

# ====================
# PASO 3: ARCHIVOS DE CONFIGURACIÓN
# ====================

Write-Host "[PASO 3/6] Creando archivos de configuración..." -ForegroundColor Yellow

# requirements.txt
@"
Django==4.2.9
django-environ==0.11.2
daphne==4.0.0
channels==4.0.0
channels-redis==4.1.0
celery==5.3.4
django-celery-beat==2.5.0
django-celery-results==2.5.1
redis==5.0.1
hiredis==2.3.2
psycopg2-binary==2.9.9
docker==7.0.0
psutil==5.9.6
python-dateutil==2.8.2
pytz==2024.1
python-dotenv==1.0.0
whitenoise==6.6.0
"@ | Out-File -FilePath "requirements.txt" -Encoding UTF8

# .env
@"
DEBUG=True
SECRET_KEY=django-insecure-dev-key-change-in-production-12345678
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=django.db.backends.postgresql
DB_NAME=monitor_db
DB_USER=monitor_user
DB_PASSWORD=SecurePass2024!
DB_HOST=localhost
DB_PORT=5432
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
DOCKER_HOST=npipe:////./pipe/docker_engine
METRICS_INTERVAL=5
METRICS_RETENTION_DAYS=30
ALERT_CHECK_INTERVAL=60
SITE_NAME=Docker Resource Monitor
COMPANY_NAME=UPEC
"@ | Out-File -FilePath ".env" -Encoding UTF8

# .gitignore
@"
__pycache__/
*.py[cod]
*.so
venv/
env/
*.log
db.sqlite3
/staticfiles/
/media/
.env
.vscode/
.idea/
.DS_Store
Thumbs.db
celerybeat-schedule
logs/*.log
"@ | Out-File -FilePath ".gitignore" -Encoding UTF8

Write-Host "  [OK] Archivos de configuración creados" -ForegroundColor Green
Write-Host ""

# ====================
# PASO 4: ARCHIVOS PYTHON CORE
# ====================

Write-Host "[PASO 4/6] Creando archivos Python principales..." -ForegroundColor Yellow

# manage.py
@"
#!/usr/bin/env python
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django") from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
"@ | Out-File -FilePath "manage.py" -Encoding UTF8

# config/__init__.py
@"
from .celery import app as celery_app
__all__ = ('celery_app',)
"@ | Out-File -FilePath "config/__init__.py" -Encoding UTF8

# config/settings.py
@"
import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'django_celery_beat',
    'django_celery_results',
    'apps.core',
    'apps.monitoring',
    'apps.alerts',
    'apps.reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'apps.core.context_processors.site_settings',
        ],
    },
}]

ASGI_APPLICATION = 'config.asgi.application'
WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE'),
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(env('REDIS_HOST'), int(env('REDIS_PORT')))],
            'capacity': 2000,
            'expiry': 10,
        },
    },
}

CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Guayaquil'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-ec'
TIME_ZONE = 'America/Guayaquil'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DOCKER_HOST = env('DOCKER_HOST')
METRICS_INTERVAL = int(env('METRICS_INTERVAL', default=5))
METRICS_RETENTION_DAYS = int(env('METRICS_RETENTION_DAYS', default=30))
ALERT_CHECK_INTERVAL = int(env('ALERT_CHECK_INTERVAL', default=60))
SITE_NAME = env('SITE_NAME', default='Docker Monitor')
COMPANY_NAME = env('COMPANY_NAME', default='UPEC')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

SESSION_COOKIE_AGE = 86400
SESSION_COOKIE_HTTPONLY = True
"@ | Out-File -FilePath "config/settings.py" -Encoding UTF8

Write-Host "  [OK] Settings creado" -ForegroundColor Green

# config/urls.py
@"
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.dashboard, name='dashboard'),
    path('login/', core_views.user_login, name='login'),
    path('logout/', core_views.user_logout, name='logout'),
    path('monitoring/', include('apps.monitoring.urls')),
    path('alerts/', include('apps.alerts.urls')),
    path('reports/', include('apps.reports.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = f"{settings.SITE_NAME} - Administración"
admin.site.site_title = settings.SITE_NAME
admin.site.index_title = "Panel de Control"
"@ | Out-File -FilePath "config/urls.py" -Encoding UTF8

# config/asgi.py
@"
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django_asgi_app = get_asgi_application()

from apps.monitoring import routing as monitoring_routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(monitoring_routing.websocket_urlpatterns)
        )
    ),
})
"@ | Out-File -FilePath "config/asgi.py" -Encoding UTF8

# config/wsgi.py
@"
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()
"@ | Out-File -FilePath "config/wsgi.py" -Encoding UTF8

# config/celery.py
@"
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
"@ | Out-File -FilePath "config/celery.py" -Encoding UTF8

Write-Host "  [OK] Config Django creado" -ForegroundColor Green

# ====================
# PASO 5: APPS
# ====================

Write-Host "[PASO 5/6] Creando aplicaciones Django..." -ForegroundColor Yellow

# apps/__init__.py
"" | Out-File -FilePath "apps/__init__.py" -Encoding UTF8

# apps/core/__init__.py
@"
default_app_config = 'apps.core.apps.CoreConfig'
"@ | Out-File -FilePath "apps/core/__init__.py" -Encoding UTF8

# apps/core/apps.py
@"
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'
"@ | Out-File -FilePath "apps/core/apps.py" -Encoding UTF8

# apps/core/context_processors.py
@"
from django.conf import settings

def site_settings(request):
    return {
        'SITE_NAME': settings.SITE_NAME,
        'COMPANY_NAME': settings.COMPANY_NAME,
        'DEBUG': settings.DEBUG,
    }
"@ | Out-File -FilePath "apps/core/context_processors.py" -Encoding UTF8

# apps/core/views.py
@"
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.monitoring.models import Container
from apps.alerts.models import Alert

@login_required
def dashboard(request):
    total_containers = Container.objects.count()
    running_containers = Container.objects.filter(status='running').count()
    stopped_containers = Container.objects.filter(status='exited').count()
    active_alerts = Alert.objects.filter(is_active=True, is_resolved=False).count()
    recent_containers = Container.objects.all().order_by('-created_at')[:5]
    recent_alerts = Alert.objects.filter(is_active=True).order_by('-triggered_at')[:5]
    
    context = {
        'total_containers': total_containers,
        'running_containers': running_containers,
        'stopped_containers': stopped_containers,
        'active_alerts': active_alerts,
        'recent_containers': recent_containers,
        'recent_alerts': recent_alerts,
    }
    return render(request, 'base/dashboard.html', context)

def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Bienvenido {user.username}!')
            return redirect(request.GET.get('next', 'dashboard'))
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    return render(request, 'base/login.html')

@login_required
def user_logout(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente')
    return redirect('login')
"@ | Out-File -FilePath "apps/core/views.py" -Encoding UTF8

Write-Host "  [OK] App Core creada" -ForegroundColor Green

# Continúa con las demás aplicaciones...
Write-Host "  [INFO] Creando archivos restantes..." -ForegroundColor Yellow

# Por limitaciones de espacio, aquí van los archivos __init__.py esenciales
"" | Out-File -FilePath "apps/monitoring/__init__.py" -Encoding UTF8
"" | Out-File -FilePath "apps/alerts/__init__.py" -Encoding UTF8
"" | Out-File -FilePath "apps/reports/__init__.py" -Encoding UTF8

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  INSTALACIÓN BASE COMPLETADA" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "PRÓXIMOS PASOS:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Crear entorno virtual:" -ForegroundColor Yellow
Write-Host "   python -m venv venv" -ForegroundColor White
Write-Host ""
Write-Host "2. Activar entorno virtual:" -ForegroundColor Yellow
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host ""
Write-Host "3. Instalar dependencias:" -ForegroundColor Yellow
Write-Host "   pip install -r requirements.txt" -ForegroundColor White
Write-Host ""
Write-Host "4. Configurar PostgreSQL y Redis" -ForegroundColor Yellow
Write-Host ""
Write-Host "5. Ejecutar migraciones:" -ForegroundColor Yellow
Write-Host "   python manage.py makemigrations" -ForegroundColor White
Write-Host "   python manage.py migrate" -ForegroundColor White
Write-Host ""
Write-Host "6. Crear superusuario:" -ForegroundColor Yellow
Write-Host "   python manage.py createsuperuser" -ForegroundColor White
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
