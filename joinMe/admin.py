from django.contrib import admin
from joinMe.models import Profile, Avatar, Event, GuestToEvent, Notification, Video, Place
from django.utils.safestring import mark_safe

class GuestsInline(admin.TabularInline):
    model = GuestToEvent
    fieldsets = [
        (None, {'fields': ['guest', 'state']})
    ]
    ordering = ('state',)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    fields = []
    readonly_fields = ['created_by', 'duration', 'created', 'video_url']
    inlines = [GuestsInline, ]

    def video_url(self, event):
        url = event.videos.last().video
        return mark_safe("<a href='{}'>{}</a>".format(url, url))


admin.site.register(Video)
admin.site.register(GuestToEvent)
admin.site.register(Place)
