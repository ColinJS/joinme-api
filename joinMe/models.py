from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis import geos
from geopy.geocoders import GoogleV3
from geopy.exc import GeocoderQueryError

from urllib.error import URLError

from django.contrib.auth.models import User
import datetime
from django.utils import timezone


class Profile(models.Model):
    init = models.BooleanField(default= False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    notification_key = models.CharField(max_length=200, default="")


class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    stripe_id = models.CharField(max_length=200, default="")
    plan = models.CharField(max_length=200, default="")


class Avatar(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    url = models.URLField()
    user = models.ForeignKey(User, related_name='avatars', on_delete=models.CASCADE)


# TODO: Ajouter User dans les fonctions, Changer la création d'une vidéo et d'un event
class Video(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name='my_videos', on_delete=models.DO_NOTHING, blank=True, null=True)
    video = models.URLField(blank=False, null=False, default='https://join-me.s3.amazonaws.com/input/video_.mov')
    # event = models.ForeignKey(Event, related_name='videos', on_delete=models.CASCADE, blank=True, null=True)


# TODO: Hide the google api key
class Place(models.Model):
    formatted_address = models.CharField(max_length=200, blank=False)
    place_id = models.CharField(max_length=200, blank=False)
    # event = models.ForeignKey(Event, related_name='place', on_delete=models.CASCADE)
    location = gis_models.PointField(u"longitude/lattitude", geography=True, blank=True, null=True)

    objects = models.Manager()

    def __unicode__(self):
        return self.formatted_address

    def save(self, **kwargs):
        if not self.location:
            address = u'%s' % self.formatted_address
            address = address.encode('utf-8')
            geocoder = GoogleV3('AIzaSyA8QQ8ADBfhHcnRn-UZFF_8lC7yGm1JLD0',)
            try:
                location_response = geocoder.geocode(address)
            except (URLError, GeocoderQueryError, ValueError):
                pass
            else:
                if location_response is not None:
                    latlon = location_response[1]
                    point = "POINT(%s %s)" % (latlon[1], latlon[0])
                    print(point)
                    self.location = geos.fromstr(point)

        super(Place, self).save()


class Friendship(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, related_name='friendship_creator', on_delete=models.CASCADE, blank=False)
    friend = models.ForeignKey(User, related_name='friendship_friend', on_delete=models.CASCADE, blank=False)
    state = models.SmallIntegerField(choices=((0, "PENDING"), (1, "ACCEPTED"), (2, "BLOCKED")), default=0)


class UserGroup(models.Model):
    created_by = models.ForeignKey(User, related_name='my_friends_groups', on_delete=models.DO_NOTHING)
    users = models.ManyToManyField(User, related_name='friends_groups')
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=200, blank=False)


class Mood(models.Model):
    title = models.CharField(max_length=200, blank=False)
    description = models.CharField(max_length=600, blank=True)


class Venue(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, related_name='my_venues', on_delete=models.CASCADE)
    followers = models.ManyToManyField(User, related_name='followed_page')
    mood = models.ForeignKey(Mood, related_name='venues', on_delete=models.DO_NOTHING)
    place = models.ForeignKey(Place, related_name='venues', on_delete=models.DO_NOTHING)
    discount = models.CharField(max_length=600, blank=True)

# TODO: Corriger le event de place to events dans touts les fichiers
class Event(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name='my_events', on_delete=models.DO_NOTHING, blank=True)
    duration = models.DurationField(blank=True, default=datetime.timedelta(hours=3))
    ending_time = models.DateTimeField(default=timezone.now()+datetime.timedelta(hours=3))
    is_public = models.BooleanField(default=False)
    videos = models.ManyToManyField(Video, related_name='event')
    place = models.ManyToManyField(Place, related_name='event')
    venue = models.ManyToManyField(Venue, related_name='events')

    @property
    def last_place(self):
        last_place = self.place.last() if self.place and self.place.last() else None
        return last_place

    def __str__(self):
        return "%s %s" % (self.created_by.first_name, self.created_by.last_name)


class GuestToEvent(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    guest = models.ForeignKey(User, related_name='events', blank=True, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, related_name='guests', blank=True, on_delete=models.CASCADE)
    state = models.SmallIntegerField(choices=((0, "PENDING"), (3, "SEEN"), (1, "ACCEPTED"), (2, "REFUSED")), default=0)

# How that's working ? Timing ?
class GuestToVenue(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    guest = models.ForeignKey(User, related_name='venues', blank=True, on_delete=models.CASCADE)
    venue = models.ForeignKey(Venue, related_name='guests', blank=True, on_delete=models.CASCADE)
    state = models.SmallIntegerField(choices=((1, "GOING"), (2, "REFUSED")), default=0)


class Notification(models.Model):
    user = models.ForeignKey(User, related_name='notifications', blank=False, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, related_name='notifications', blank=False, on_delete=models.CASCADE)
    type_of_notification = models.SmallIntegerField(choices=((0, "NEW_INVITATION"), (1, "SOMEONE_COMING")), default=0)
    state = models.SmallIntegerField(choices=((0, "UNSEEN"), (1, "SEEN")), default=0)
    created = models.DateTimeField(auto_now_add=True)


class Comment(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name='event_comments', on_delete=models.CASCADE)
    event = models.ForeignKey(Event, related_name='comments', on_delete=models.CASCADE)
    message = models.CharField(max_length=600, blank=False)

# class Page(models.Model):
#    created = models.DateTimeField(auto_now_add=True)
#    created_by = models.ForeignKey(User, related_name='my_page', on_delete=models.DO_NOTHING)
#    followers = models.ManyToManyField(User, related_name='followed_page')
#    events = models.ManyToManyField(Event, related_name='pages')
#    name = models.CharField(max_length=200, blank=False)
#    description = models.CharField(max_length=600, blank=True)


