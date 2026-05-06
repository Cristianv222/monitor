from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/server/$', consumers.ServerMetricsConsumer.as_asgi()),
    re_path(r'ws/metrics/(?P<sub_id>\d+)/$', consumers.SubscriptionMetricsConsumer.as_asgi()),
    re_path(r'ws/logs/(?P<container_id>[a-zA-Z0-9_-]+)/$', consumers.ContainerLogsConsumer.as_asgi()),
]
