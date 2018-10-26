from rest_framework import serializers
from joinMe.models import Friendship, Profile, Avatar, Event, Video, UserGroup
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth import get_user_model


class SimpleUserSerializer(serializers.ModelSerializer):

    @property
    def is_friend(self):
        current_user = get_user_model()
        if current_user != AnonymousUser:
            from django.db.models import Q
            return (len(Friendship.objects.filter(Q(creator__pk=current_user.pk, friend__pk=self.validated_data['id']) |
                                                  Q(creator__pk=self.validated_data['id'], friend__pk=current_user.pk)).first()) > 0)
        else:
            return False

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'avatars', 'is_friend')


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
