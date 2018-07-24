from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User, Group
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from oauth2_provider.views.generic import ProtectedResourceView
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import renderers
from rest_framework import generics
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404

import os
import requests

from joinMe.models import Friendship, Profile, Avatar, Event, Video
from joinMe.serializers import FriendshipSerializer, UserSerializer, AvatarSerializer, EventSerializer, VideoSerializer


# TODO: Add try and catch and test ...
class FirstConnection(APIView):

    def get(self, request, format=None):

        if request.auth:
            user = request.user

            if len(Profile.objects.filter(user__pk=user.pk)) or not user.profile.init:

                # Get the avatar url of the user and store it
                # TODO: Check if the avatar already exist
                response = requests.get(
                    'https://graph.facebook.com/me/picture',
                    params={'access_token': user.social_auth.get(provider="facebook").extra_data['access_token'],
                            'redirect': False}
                )
                if response.status_code == 200:
                    # return Response(user.avatars.all()[0].url)
                    # Create a new avatar object with the facebook url
                    avatar = Avatar(url= response.json()["data"]["url"], user=user)
                    avatar.save()

                # Get the friends list and recreate friends relationships
                # TODO: not allowed to have duplicate relationship like A->B and B->A, So check before to add one
                response = requests.get(
                    'https://graph.facebook.com/me/friends',
                    params={'access_token': user.social_auth.get(provider="facebook").extra_data['access_token']}
                )

                if response.status_code == 200:
                    friends = []
                    for friend in response.json()["data"]:
                        friends = User.objects.filter(social_auth__uid=friend['id'])

                    for friend in friends:
                        friendship = Friendship(creator=user, friend=friend, state=1)
                        friendship.save()

                profile = Profile(user=request.user, init=True)
                profile.save()


        return Response({'init': True})


class EventList(APIView):

    def post(self, request):

        if request.auth:
            user = request.user

            with transaction.atomic():
                video = Video(video=request.FILES['video'])
                video.save()

                event = Event(created_by=user)
                event.save()
                event.videos.set([video])
                event.save()

                return Response(request.build_absolute_uri(user.my_events.last().videos.last().video.url))

    def get(self, request):

        if request.auth:
            user = request.user

            my_events = user.my_events.all()
            events = user.events.all()

            ctx = {'my_events': [], 'events': []}

            for my_event in my_events:
                new_event = {
                    'id': my_event.pk,
                    'creator': {
                        'url': my_event.created_by.avatars.last().url,
                        'first_name': my_event.created_by.first_name,
                        'last_name': my_event.created_by.last_name
                    },
                    'creation_date': my_event.created,
                    'video_url': request.build_absolute_uri(my_event.videos.last().video.url)
                }
                ctx['my_events'].append(new_event)

            for event in events:
                new_event = {
                    'id': event.pk,
                    'creator': {
                        'url': event.created_by.avatars.last().url,
                        'first_name': event.created_by.first_name,
                        'last_name': event.created_by.last_name
                    },
                    'creation_date': event.created,
                    'video_url': request.build_absolute_uri(event.videos.last().video.url)
                }
                ctx['events'].append(new_event)

            return Response(ctx)


@csrf_exempt
def getEventDetails(request):
    # TODO: return the event info
    pass


class FriendList(APIView):

    def get(self, request):
        if request.auth:
            user = request.user

            create_friendship = Friendship.objects.distinct().filter(creator__pk=user.pk)
            friend_friendship = Friendship.objects.distinct().filter(friend__pk=user.pk)

            ctx = {'friends': []}
            for friend in create_friendship:
                new_friend = {
                    'id': friend.friend.pk,
                    'first_name': friend.friend.first_name,
                    'last_name': friend.friend.last_name
                }
                ctx['friends'].append(new_friend)

            for friend in friend_friendship:
                new_friend = {
                    'id': friend.friend.pk,
                    'first_name': friend.friend.first_name,
                    'last_name': friend.friend.last_name
                }
                ctx['friends'].append(new_friend)

            return Response(ctx)

class ShareingEvent(APIView):

    def put(self, request, event_id):

        if request.auth:
            user = request.user

            event = get_object_or_404(Event, pk=event_id)

            if event.created_by == user or event.guests.filter(pk=user.pk):

                friend_id = request.data['friend_id']
                friend = get_object_or_404(User, pk=friend_id)
                print([friend.__dict__[x] for x in friend.__dict__.keys() if not x.startswith('_')])
                event.guests.add(friend)
                event.save()

            ctx = {'response': []}
            guests = event.guests.all()

            for guest in guests:
                new_guest = {
                    'name': guest.last_name,
                }
                ctx['response'].append(new_guest)

            return Response(ctx)

        return Response({'response': request.auth})
