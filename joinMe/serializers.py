from rest_framework import serializers
from joinMe.models import Friendship, Profile, Avatar, Event, Video, UserGroup
from django.contrib.auth.models import User


class SimpleUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'avatars')


class UserGroupSerializer(serializers.ModelSerializer):

    created_by = SimpleUserSerializer(read_only=True)
    users = SimpleUserSerializer(read_only=True, many=True)

    class Meta:
        model = UserGroup
        fields = ['id', 'name', 'users', 'created_by']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'avatars')


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ()


class AvatarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avatar
        fields = ('id', 'url', 'user', 'created')


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ('id', 'videos', 'created', 'created_by', 'guests')


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ('id', 'url', 'created', 'event')


class FriendshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'created', 'creator', 'friend', 'state')
