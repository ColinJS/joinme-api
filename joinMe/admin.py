from django.contrib import admin
from joinMe.models import Profile, Avatar, Event, GuestToEvent, Notification, Video, Place
from django.utils.safestring import mark_safe

class GuestsInline(admin.TabularInline):
    model = GuestToEvent
    fieldsets = [
        (None, {'fields': ['guest', 'state']})
    ]
    ordering = ('state',)
    extra = 0

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    readonly_fields = ['created_by', 'duration', 'created', 'video_view']
    inlines = [GuestsInline, ]
    search_fields = ['created_by__first_name', 'created_by__last_name', 'created_by__pk']

    def video_view(self, event):
        url = event.videos.last().video
        return mark_safe("<video controls><source src='{}' type='video/mp4'></video>".format(url))

    def video_view_little(self, event):
        url = event.videos.last().video
        return mark_safe("<video height='200' controls><source src='{}' type='video/mp4'></video>".format(url))

    list_display = ['created_by', 'created', 'video_view_little', ]


admin.site.register(Video)
admin.site.register(GuestToEvent)
admin.site.register(Place)
