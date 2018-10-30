from rest_framework import serializers
from joinMe.models import Friendship, Profile, Avatar, Event, Video, UserGroup, Comment
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth import get_user_model

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class SimpleUserSerializer(serializers.ModelSerializer):

    is_friend = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    def get_is_friend(self, user):
        current_user = self.context['request'].user
        if current_user != AnonymousUser:
            from django.db.models import Q
            return (Friendship.objects.filter(Q(creator__pk=current_user.pk, friend__pk=user.id) |
                                              Q(creator__pk=user.id, friend__pk=current_user.pk)).first() is not None)
        else:
            return False

    def get_avatar(self, user):
        avatar = (user.avatars.last().url if user.avatars and user.avatars.last() else '')
        return avatar

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'avatar', 'is_friend')


class UserGroupSerializer(serializers.ModelSerializer):

    created_by = SimpleUserSerializer(read_only=True)
    users = SimpleUserSerializer(read_only=True, many=True)

    class Meta:
        model = UserGroup
        fields = ['id', 'name', 'users', 'created_by']


class UserGroupListSerializer(serializers.ModelSerializer):

    created_by = SimpleUserSerializer(read_only=True)

    class Meta:
        model = UserGroup
        fields = ['id', 'name', 'users', 'created_by']


class CommentSerializer(serializers.ModelSerializer):

    created_by = SimpleUserSerializer(read_only=True, many=False)

    def create(self, validated_data):
        super().save(validated_data)

        event_id = validated_data.get('event')
        message = validated_data.get('message')

        channel_layer = get_channel_layer()
        event_group_name = 'event_%s' % event_id
        async_to_sync(channel_layer.group_send)(event_group_name, {
            "type": "comment.change",
            "action": "add",
            "comment": {"event_id": event_id, "comment": message}
        })

    class Meta:
        model = Comment
        fields = ['id', 'created_by', 'event', 'message']


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
