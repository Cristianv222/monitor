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

admin.site.site_header = f"{settings.SITE_NAME} - AdministraciÃ³n"
admin.site.site_title = settings.SITE_NAME
admin.site.index_title = "Panel de Control"
