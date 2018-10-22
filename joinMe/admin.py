from django.contrib import admin
from joinMe.models import Profile, Avatar, Event, GuestToEvent, Notification, Video, Place

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    fields = ('created_by', 'duration', 'videos', 'guests', 'place')


admin.site.register(Video)
admin.site.register(GuestToEvent)
admin.site.register(Place)
