from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Sum, Avg, Count
from apps.monitoring.models import Container
from apps.alerts.models import Alert
from apps.billing.models import Client, Subscription, SystemSettings
import docker

@login_required
def dashboard(request):
    from django.conf import settings
    print(f"DEBUG: LOGIN_URL is {settings.LOGIN_URL}")
    total_containers = Container.objects.count()
    running_containers = Container.objects.filter(status='running').count()
    stopped_containers = Container.objects.filter(status='exited').count()
    active_alerts = Alert.objects.filter(is_active=True, is_resolved=False).count()
    recent_containers = Container.objects.all().order_by('-created_at')[:5]
    recent_alerts = Alert.objects.filter(is_active=True).order_by('-triggered_at')[:5]
    
    active_subs = Subscription.objects.filter(status='active').count()
    suspended_subs = Subscription.objects.filter(status='suspended').count()
    
    context = {
        'total_containers': total_containers,
        'running_containers': running_containers,
        'stopped_containers': stopped_containers,
        'active_alerts': active_alerts,
        'recent_containers': recent_containers,
        'recent_alerts': recent_alerts,
        'active_subs': active_subs,
        'suspended_subs': suspended_subs,
    }
    return render(request, 'base/dashboard.html', context)

@login_required
def clients_list(request):
    clients = Client.objects.prefetch_related('subscriptions').all().order_by('-created_at')
    unassigned_containers = Container.objects.filter(subscription__isnull=True).order_by('name')
    
    # Group unassigned by project_name
    unassigned_projects = {}
    for c in unassigned_containers:
        proj = c.project_name or 'standalone'
        if proj not in unassigned_projects:
            unassigned_projects[proj] = []
        unassigned_projects[proj].append(c)
        
    context = {
        'clients': clients,
        'unassigned_projects': unassigned_projects,
    }
    return render(request, 'base/clients.html', context)

@login_required
@require_POST
def create_client(request):
    name = request.POST.get('name')
    cedula_ruc = request.POST.get('cedula_ruc')
    email = request.POST.get('email')
    phone = request.POST.get('phone')
    address = request.POST.get('address')
    
    if name and cedula_ruc and email:
        try:
            Client.objects.create(
                name=name,
                cedula_ruc=cedula_ruc,
                email=email,
                phone=phone,
                address=address
            )
            messages.success(request, 'Cliente creado correctamente.')
        except Exception as e:
            messages.error(request, f'Error al crear cliente: {e}')
    else:
        messages.error(request, 'Razón Social, Cédula/RUC y Correo son obligatorios.')
        
    return redirect('clients_list')

@login_required
@require_POST
def create_subscription(request):
    client_id = request.POST.get('client_id')
    plan_name = request.POST.get('plan_name')
    price = request.POST.get('price')
    cutoff_day = request.POST.get('cutoff_day')
    
    if client_id and plan_name and price and cutoff_day:
        try:
            client = Client.objects.get(id=client_id)
            Subscription.objects.create(
                client=client,
                plan_name=plan_name,
                price=price,
                cutoff_day=cutoff_day
            )
            messages.success(request, 'Suscripción creada correctamente.')
        except Client.DoesNotExist:
            messages.error(request, 'Cliente inválido.')
    else:
        messages.error(request, 'Todos los campos son obligatorios.')
        
    return redirect('clients_list')

@login_required
@require_POST
def assign_containers(request):
    subscription_id = request.POST.get('subscription_id')
    project_names = request.POST.getlist('project_names')
    
    if subscription_id and project_names:
        try:
            sub = Subscription.objects.get(id=subscription_id)
            containers_updated = 0
            for proj in project_names:
                # Assign all unassigned containers with this project_name to the subscription
                if proj == 'standalone':
                    containers = Container.objects.filter(subscription__isnull=True, project_name__in=[None, '', 'standalone'])
                else:
                    containers = Container.objects.filter(subscription__isnull=True, project_name=proj)
                
                for container in containers:
                    container.subscription = sub
                    container.save()
                    containers_updated += 1
                    
            messages.success(request, f'{containers_updated} contenedor(es) del proyecto asignado(s) exitosamente a {sub.client.name}.')
        except Subscription.DoesNotExist:
            messages.error(request, 'Suscripción inválida.')
    else:
        messages.error(request, 'Debe seleccionar una suscripción y al menos un proyecto (Stack).')
        
    return redirect('clients_list')

@login_required
@require_POST
def unlink_container(request):
    container_id = request.POST.get('container_id')
    if container_id:
        try:
            container = Container.objects.get(container_id=container_id)
            client_name = container.subscription.client.name if container.subscription else "cliente"
            container.subscription = None
            container.save()
            messages.success(request, f'Contenedor desvinculado de {client_name}.')
        except Container.DoesNotExist:
            messages.error(request, 'Contenedor no encontrado.')
    return redirect('containers_list')

@login_required
def subscription_metrics(request, sub_id):
    sub = get_object_or_404(Subscription, id=sub_id)
    # Get last 50 metrics for initial chart load (historical data)
    containers = sub.containers.all()
    
    # We will pass the subscription details and let WebSocket handle the live data
    context = {
        'subscription': sub,
        'client': sub.client,
        'containers': containers
    }
    return render(request, 'base/metrics.html', context)

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

@login_required
def containers_list(request):
    # Agrupar contenedores asignados por cliente
    clients = Client.objects.prefetch_related('subscriptions__containers').all()
    
    # Contenedores no asignados
    unassigned_containers = Container.objects.filter(subscription__isnull=True).order_by('-created_at')
    
    unassigned_projects = {}
    for c in unassigned_containers:
        proj = c.project_name or 'standalone'
        if proj not in unassigned_projects:
            unassigned_projects[proj] = []
        unassigned_projects[proj].append(c)
    
    context = {
        'clients': clients,
        'unassigned_projects': unassigned_projects
    }
    return render(request, 'base/containers.html', context)

@login_required
@require_POST
def container_action(request):
    container_id = request.POST.get('container_id')
    action = request.POST.get('action') # 'start', 'stop', 'restart'
    
    if container_id and action in ['start', 'stop', 'restart']:
        try:
            client = docker.from_env()
            container = client.containers.get(container_id)
            
            project_name = container.labels.get('com.docker.compose.project')
            if project_name == 'monitor':
                messages.warning(request, 'Por seguridad, no puedes apagar o reiniciar los contenedores del propio Monitor desde aquí.')
                return redirect('containers_list')
            
            if action == 'start':
                container.start()
                messages.success(request, f'Contenedor {container.name} iniciado.')
            elif action == 'stop':
                container.stop()
                messages.success(request, f'Contenedor {container.name} detenido.')
            elif action == 'restart':
                container.restart()
                messages.success(request, f'Contenedor {container.name} reiniciado.')
                
        except Exception as e:
            messages.error(request, f'Error al ejecutar {action}: {str(e)}')
    else:
        messages.error(request, 'Parámetros inválidos.')
        
    return redirect('containers_list')

@login_required
def admin_settings(request):
    settings, created = SystemSettings.objects.get_or_create(id=1)
    
    if request.method == 'POST':
        cost = request.POST.get('vps_monthly_cost')
        ram_total = request.POST.get('total_server_ram_gb')
        if cost:
            settings.vps_monthly_cost = cost
        if ram_total:
            settings.total_server_ram_gb = ram_total
        settings.save()
        messages.success(request, 'Configuración actualizada correctamente.')
        return redirect('admin_settings')

    # Financial Stats
    active_subscriptions = Subscription.objects.filter(status='active')
    total_income = active_subscriptions.aggregate(Sum('price'))['price__sum'] or 0
    total_cost = settings.vps_monthly_cost
    profit_margin = total_income - total_cost
    
    # Resource Analysis per Subscription
    sub_analysis = []
    
    # Cost per MB of server RAM
    server_total_mb = float(settings.total_server_ram_gb) * 1024
    cost_per_mb = float(total_cost) / server_total_mb if server_total_mb > 0 else 0
    
    for sub in active_subscriptions:
        containers = sub.containers.all()
        total_ram = 0
        total_cpu = 0
        total_estimated_cost = 0
        
        for container in containers:
            # Try to get monthly average first, then hourly, then latest
            monthly = container.monthly_metrics.first()
            if monthly:
                ram = monthly.avg_ram_mb
                cpu = monthly.avg_cpu_percent
            else:
                hourly = container.hourly_metrics.all()[:24].aggregate(Avg('avg_ram_mb'), Avg('avg_cpu_percent'))
                ram = hourly['avg_ram_mb__avg'] or 0
                cpu = hourly['avg_cpu_percent__avg'] or 0
                
            if ram == 0: # Fallback to latest
                last_metric = container.metrics.first()
                if last_metric:
                    ram = last_metric.ram_mb
                    cpu = last_metric.cpu_percent
            
            total_ram += ram
            total_cpu += cpu
            total_estimated_cost += ram * cost_per_mb
        
        # Efficiency Score: Price / RAM (USD per MB)
        efficiency = float(sub.price) / (total_ram + 1) 
        
        # Recommended price based on resource consumption (cost * 2 for margin)
        recommended = total_estimated_cost * 2 + 5 # Base margin
        
        sub_analysis.append({
            'subscription': sub,
            'ram_usage': round(total_ram, 1),
            'cpu_usage': round(total_cpu, 1),
            'estimated_cost': round(total_estimated_cost, 2),
            'efficiency': round(efficiency, 3),
            'recommended_price': round(recommended, 2)
        })

    context = {
        'settings': settings,
        'total_income': total_income,
        'total_cost': total_cost,
        'profit_margin': profit_margin,
        'sub_analysis': sub_analysis,
        'cost_per_mb': cost_per_mb
    }
    return render(request, 'base/admin_settings.html', context)
