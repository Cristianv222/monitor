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
            messages.error(request, 'Usuario o contraseÃ±a incorrectos')
    return render(request, 'base/login.html')

@login_required
def user_logout(request):
    logout(request)
    messages.info(request, 'Has cerrado sesiÃ³n correctamente')
    return redirect('login')
