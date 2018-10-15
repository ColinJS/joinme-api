
from django.conf.urls import url

from . import consumers

websocket_urlpatterns = [
    url(r'^ws/event/(?P<event_id>[0-9]+)/$', consumers.EventConsumer),
    url(r'^ws/user/(?P<user_id>[0-9]+)/$', consumers.EventConsumer),
]