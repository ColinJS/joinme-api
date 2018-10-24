from rest_framework import serializers
from joinMe.models import Friendship, Profile, Avatar, Event, Video, UserGroup
from django.contrib.auth.models import User


class UserGroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserGroup
        fields = ['pk', 'name', 'users']
        read_only_fields = ['created_by']

    def create(self, validated_data):
        name = validated_data['name']
        created_by = validated_data['created_by']
        users = validated_data['users'].append(created_by.pk)
        UserGroup.objects.create(name=name, created_by=created_by, users=users)



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
