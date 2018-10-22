from django.contrib import admin
from joinMe.models import Profile, Avatar, Event, GuestToEvent, Notification, Video, Place

class GuestsInline(admin.TabularInline):
    model = GuestToEvent
    fieldsets = [
        (None, {'fields': ['guest', 'state']})
    ]

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    inlines = [GuestsInline, ]


admin.site.register(Video)
admin.site.register(GuestToEvent)
admin.site.register(Place)
