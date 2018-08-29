from django.conf.urls import url
from joinMe import views

urlpatterns = [
    url(r'^init$', views.FirstConnection.as_view()),
    url(r'^events$', views.EventList.as_view()),
    url(r'^friends$', views.FriendList.as_view()),
    url(r'^(?P<event_id>[0-9]+)\/share$', views.SharingEvent.as_view()),
    url(r'^events/(?P<event_id>[0-9]+)$', views.EventDetails.as_view()),
    url(r'^sign_s3$', views.aws_s3_interface.as_view()),
    url(r'^notification$', views.Notifications.as_view()),
]