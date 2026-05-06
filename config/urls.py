from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.core import views as core_views
from apps.billing import views as billing_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.dashboard, name='dashboard'),
    path('clients/', core_views.clients_list, name='clients_list'),
    path('clients/create/', core_views.create_client, name='create_client'),
    path('subscriptions/create/', core_views.create_subscription, name='create_subscription'),
    path('subscriptions/<int:sub_id>/metrics/', core_views.subscription_metrics, name='subscription_metrics'),
    path('containers/', core_views.containers_list, name='containers_list'),
    path('containers/assign/', core_views.assign_containers, name='assign_containers'),
    path('containers/action/', core_views.container_action, name='container_action'),
    path('admin-panel/', core_views.admin_settings, name='admin_settings'),
    path('login/', core_views.user_login, name='login'),
    path('logout/', core_views.user_logout, name='logout'),
    
    # API endpoints
    path('api/billing/status/', billing_views.client_status_api, name='api_billing_status'),
    
    path('monitoring/', include('apps.monitoring.urls')),
    path('alerts/', include('apps.alerts.urls')),
    path('reports/', include('apps.reports.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = f"{settings.SITE_NAME} - AdministraciÃ³n"
admin.site.site_title = settings.SITE_NAME
admin.site.index_title = "Panel de Control"
