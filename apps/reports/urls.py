from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('consumption/', views.consumption_report, name='consumption_report'),
]
