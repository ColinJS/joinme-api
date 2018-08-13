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
import datetime
from django.utils import timezone

import requests, os, boto3
import json
import subprocess

from joinMe.models import Friendship, Profile, Avatar, Event, Video, GuestToEvent, Place
from joinMe.serializers import FriendshipSerializer, UserSerializer, AvatarSerializer, EventSerializer, VideoSerializer


# TODO: Add try and catch and test ...
class FirstConnection(APIView):

    def get(self, request, format=None):

        if request.auth:
            user = request.user

            if len(Profile.objects.filter(user__pk=user.pk)) == 0 or not user.profile.init:

                # Get the avatar url of the user and store it
                # TODO: Check if the avatar already exist
                response = requests.get(
                    'https://graph.facebook.com/me/picture',
                    params={'access_token': user.social_auth.get(provider="facebook").extra_data['access_token'],
                            'redirect': False,
                            'type': 'large',
                            }
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
                        friends.append(User.objects.get(social_auth__uid=friend['id']))

                    for friend in friends:
                        friendship = Friendship(creator=user, friend=friend, state=1)
                        friendship.save()

                profile = Profile(user=request.user, init=True)
                profile.save()

            ctx = {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'avatar': user.avatars.last().url,
            }

            return Response(ctx)

        return Response({'init': True})


class EventList(APIView):

    def post(self, request):
        # TODO: convert mov file to mp4
        print("Starting to process the video upload ...")
        if request.auth:
            user = request.user
            data = request.data
            place = {'formatted_address': '', 'place_id': ''}
            duration = datetime.timedelta(hours=3)

            if 'place' in data:
                place = data['place']

            if 'duration' in data:
                duration = datetime.timedelta(hours=int(data['duration']['hours']), minutes=int(data['duration']['minutes']))

            if 'video' in data:
                with transaction.atomic():
                    url = data['video'].replace('/input/', '/output/').split('.')[0]+".mp4"

                    video = Video(video=url)
                    video.save()

                    event = Event(created_by=user, duration=duration, ending_time=timezone.now()+duration)
                    event.save()
                    event.videos.set([video])
                    event.save()

                    place = Place(formatted_address=place['formatted_address'], place_id=place['place_id'], event=event)
                    place.save()

                    if 'friends' in data:
                        for f in data['friends']:
                            f_user = User.objects.filter(pk=f['id']).first()
                            if f_user:
                                sharing = GuestToEvent(guest=f_user, event=event, state=0)
                                sharing.save()

            ctx = {
                'id': user.my_events.last().id,
                'uri': data['video']
            }

            return Response(ctx)

        return Response({'error': 'Not added ...'})

    def get(self, request):
        # TODO: my_events must not be used for fetching event of the user, only to now who's the creator of an event
        if request.auth:
            user = request.user
            now = timezone.now()

            my_events = user.my_events.filter(ending_time__gte=now)
            events = []

            for e in user.events.all():
                if e.event not in events and e.event.ending_time >= now:
                    events.append(e.event)

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
                    'video_url': my_event.videos.last().video
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
                    'video_url': event.videos.last().video
                }
                ctx['events'].append(new_event)

            return Response(ctx)

        return Response({'response': request.auth})


class EventDetails(APIView):
    # TODO: return the event info
    def get(self, request, event_id):
        if request.auth:
            user = request.user

            event = get_object_or_404(Event, pk=event_id)
            guests = event.guests.all()
            ctx = {
                'video_url': event.videos.last().video,
                'creation_date': event.created,
                'id': event.pk,
                'place': {
                    'formatted_address': event.place.last().formatted_address,
                    'place_id': event.place.last().place_id,
                },
                'ending_date': event.ending_time,
                'guests': [],
            }

            for guest in guests:
                new_guest = {
                    'first_name': guest.guest.first_name,
                    'last_name': guest.guest.last_name,
                    'state': guest.state,
                    'avatar': guest.guest.avatars.last().url,
                    'id': guest.guest.pk,
                }
                if new_guest not in ctx['guests']:
                    ctx['guests'].append(new_guest)

            return Response(ctx)

        return Response({'response': request.auth})

    def put(self, request, event_id):
        if request.auth:
            user = request.user
            data = request.data

            if 'coming' in data:
                guestToEvent = GuestToEvent.objects.filter(event__pk=event_id, guest__pk=user.pk)
                for g in guestToEvent:
                    g.state = data['coming']
                    g.save()
                return Response({'message': 'Update your state to the event is done'})

            return Response({'message': 'Can\'t find coming variable'})

        return Response({'response': request.auth})




class FriendList(APIView):

    def get(self, request):
        if request.auth:
            user = request.user

            create_friendship = Friendship.objects.distinct().filter(creator__pk=user.pk).filter(state=1)
            friend_friendship = Friendship.objects.distinct().filter(friend__pk=user.pk).filter(state=1)

            ctx = {'friends': []}
            for friend in create_friendship:
                new_friend = {
                    'id': friend.friend.pk,
                    'first_name': friend.friend.first_name,
                    'last_name': friend.friend.last_name,
                    'avatar': friend.friend.avatars.last().url if friend.friend.avatars and friend.friend.avatars.last() else '',
                }
                ctx['friends'].append(new_friend)

            for friend in friend_friendship:
                myId = friend.creator.pk
                if len([c for c in ctx['friends'] if myId == c['id']]) == 0:
                    new_friend = {
                        'id': friend.creator.pk,
                        'first_name': friend.creator.first_name,
                        'last_name': friend.creator.last_name,
                        'avatar': friend.creator.avatars.last().url if friend.creator.avatars and friend.creator.avatars.last() else '',
                    }
                    ctx['friends'].append(new_friend)

            return Response(ctx)

        return Response({'response': request.auth})

class SharingEvent(APIView):

    def put(self, request, event_id):

        if request.auth:
            user = request.user

            event = get_object_or_404(Event, pk=event_id)

            if event.created_by == user or event.guests.guest.filter(pk=user.pk):

                friends = []
                for f in request.data['friends']:
                    f_user = User.objects.filter(pk=f['id']).first()
                    if f_user:
                        sharing = GuestToEvent(guest=f_user, event=event, state=0)
                        sharing.save()

            ctx = {'response': []}
            guests = [gte.guest for gte in GuestToEvent.objects.filter(event__pk=event.pk)]

            for guest in guests:
                new_guest = {
                    'name': guest.last_name,
                }
                ctx['response'].append(new_guest)

            return Response(ctx)

        return Response({'response': request.auth})


class aws_s3_interface(APIView):

    def get(self, request):
        S3_BUCKET = os.environ.get('S3_BUCKET')

        filename = request.GET.get('filename', '')
        filetype = request.GET.get('filetype', '')

        s3 = boto3.client('s3')

        presigned_post = s3.generate_presigned_post(
            Bucket=S3_BUCKET,
            Key=filename,
            Fields={"acl": "public-read", "Content-Type": filetype},
            Conditions=[
                {"acl": "public-read"},
                {"Content-Type": filetype}
            ],
            ExpiresIn=3600
        )

        return Response({
            'data': presigned_post,
            'url': 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, filename)
        })
