from django.db import models
from django.contrib.auth.models import User


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
    guests = models.ManyToManyField(User, related_name='events', blank=True)


class Video(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    video = models.FileField(upload_to='videos/', blank=False, null=False, default='media/anonymous.mp4')
    event = models.ForeignKey(Event, related_name='videos', on_delete=models.CASCADE, blank=True, null=True)


class Friendship(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, related_name='friendship_creator', on_delete=models.CASCADE, blank=False)
    friend = models.ForeignKey(User, related_name='friendship_friend', on_delete=models.CASCADE, blank=False)
    state = models.SmallIntegerField(choices=((0, "PENDING"), (1, "ACCEPTED"), (2, "BLOCKED")), default="PENDING")
