from django.contrib import admin
from joinMe.models import Profile, Avatar, Event, GuestToEvent, Notification


class EventAdmin(admin.ModelAdmin):
    fields = ('created_by', 'duration', 'videos', 'guests', 'place')


admin.site.register(Event, EventAdmin)



