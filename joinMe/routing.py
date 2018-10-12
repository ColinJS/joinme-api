
from django.conf.urls import url

from . import consumers

websocket_urlpatterns = [
    url(r'^ws/event/(?P<event_id>[^/]+)/$', consumers.EventConsumer),
]