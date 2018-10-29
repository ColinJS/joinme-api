from django.db import models
from django.contrib.auth.models import User
import datetime
from django.utils import timezone


class Profile(models.Model):
    init = models.BooleanField(default= False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    notification_key = models.CharField(max_length=200, default="")


class Avatar(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    url = models.URLField()
    user = models.ForeignKey(User, related_name='avatars', on_delete=models.CASCADE)


class Event(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name='my_events', on_delete=models.DO_NOTHING, blank=True)
    duration = models.DurationField(blank=True, default=datetime.timedelta(hours=3))
    ending_time = models.DateTimeField(default=timezone.now()+datetime.timedelta(hours=3))

    def __str__(self):
        return "%s %s" % (self.created_by.first_name, self.created_by.last_name)


class Video(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    video = models.URLField(blank=False, null=False, default='https://join-me.s3.amazonaws.com/input/video_.mov')
    event = models.ForeignKey(Event, related_name='videos', on_delete=models.CASCADE, blank=True, null=True)


class Friendship(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, related_name='friendship_creator', on_delete=models.CASCADE, blank=False)
    friend = models.ForeignKey(User, related_name='friendship_friend', on_delete=models.CASCADE, blank=False)
    state = models.SmallIntegerField(choices=((0, "PENDING"), (1, "ACCEPTED"), (2, "BLOCKED")), default=0)


class GuestToEvent(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    guest = models.ForeignKey(User, related_name='events', blank=True, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, related_name='guests', blank=True, on_delete=models.CASCADE)
    state = models.SmallIntegerField(choices=((0, "PENDING"), (1, "ACCEPTED"), (2, "REFUSED")), default=0)


class Place(models.Model):
    formatted_address = models.CharField(max_length=200, blank=False)
    place_id = models.CharField(max_length=200, blank=False)
    event = models.ForeignKey(Event, related_name='place', on_delete=models.CASCADE)


class Notification(models.Model):
    user = models.ForeignKey(User, related_name='notifications', blank=False, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, related_name='notifications', blank=False, on_delete=models.CASCADE)
    type_of_notification = models.SmallIntegerField(choices=((0, "NEW_INVITATION"), (1, "SOMEONE_COMING")), default=0)
    state = models.SmallIntegerField(choices=((0, "UNSEEN"), (1, "SEEN")), default=0)
    created = models.DateTimeField(auto_now_add=True)


class UserGroup(models.Model):
    created_by = models.ForeignKey(User, related_name='my_friends_groups', on_delete=models.DO_NOTHING)
    users = models.ManyToManyField(User, related_name='friends_groups')
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=200, blank=False)


class Comment(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name='event_comments', on_delete=models.CASCADE)
    event = models.ForeignKey(User, related_name='comments', on_delete=models.CASCADE)
    message = models.CharField(max_length=600, blank=False)
