from django.db import models
from django.contrib.auth.models import User
import datetime
from django.utils import timezone

class Profile(models.Model):
    init = models.BooleanField(default= False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)


class Avatar(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    url = models.URLField()
    user = models.ForeignKey(User, related_name='avatars', on_delete=models.CASCADE)


class Event(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name='my_events', on_delete=models.DO_NOTHING, blank=True)
    duration = models.DurationField(blank=True, default=datetime.timedelta(hours=3))
    ending_time = models.DateTimeField(default=timezone.now()+datetime.timedelta(hours=3))



class Video(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    video = models.URLField(blank=False, null=False, default='https://join-me.s3.amazonaws.com/input/video_.mov')
    event = models.ForeignKey(Event, related_name='videos', on_delete=models.CASCADE, blank=True, null=True)


class Friendship(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, related_name='friendship_creator', on_delete=models.CASCADE, blank=False)
    friend = models.ForeignKey(User, related_name='friendship_friend', on_delete=models.CASCADE, blank=False)
    state = models.SmallIntegerField(choices=((0, "PENDING"), (1, "ACCEPTED"), (2, "BLOCKED")), default="PENDING")


class GuestToEvent(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    guest = models.ForeignKey(User, related_name='events', blank=True, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, related_name='guests', blank=True, on_delete=models.CASCADE)
    state = models.SmallIntegerField(choices=((0, "PENDING"), (1, "ACCEPTED"), (2, "REFUSED")), default="PENDING")


class Place(models.Model):
    formatted_address = models.CharField(max_length=200, blank=False)
    place_id = models.CharField(max_length=200, blank=False)
    event = models.ForeignKey(Event, related_name='place', on_delete=models.CASCADE)
