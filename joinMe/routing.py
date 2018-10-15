
from django.conf.urls import url

from . import consumers

websocket_urlpatterns = [
    url(r'^ws/(?P<token>[0-9A-Za-z]+)/event/(?P<event_id>[0-9]+)/$', consumers.EventConsumer),
    url(r'^ws/(?P<token>[0-9A-Za-z]+)/user/(?P<user_id>[0-9]+)/$', consumers.UserConsumer),
]