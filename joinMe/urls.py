from django.conf.urls import url
from joinMe import views
from rest_framework import routers

url_router = routers.SimpleRouter()
url_router.register(r'groups', views.UserGroupEndPoint)

urlpatterns = [
    url(r'^init$', views.FirstConnection.as_view()),
    url(r'^users$', views.Users.as_view()),
    url(r'^events$', views.EventList.as_view()),
    url(r'^friends$', views.FriendList.as_view()),
    url(r'^friends/(?P<user_id>[0-9]+)\/state', views.FriendshipManager.as_view()),
    url(r'^(?P<event_id>[0-9]+)\/share$', views.SharingEvent.as_view()),
    url(r'^events/(?P<event_id>[0-9]+)$', views.EventDetails.as_view()),
    url(r'^events/(?P<event_id>[0-9]+)\/web$', views.EventDetailsForWeb.as_view(), name="web_event_details"),
    url(r'^sign_s3$', views.aws_s3_interface.as_view()),
    url(r'^notifications$', views.Notifications.as_view()),
    url(r'^me$', views.Me.as_view()),
]
urlpatterns += url_router.urls