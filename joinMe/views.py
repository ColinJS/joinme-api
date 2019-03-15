from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from rest_framework.views import APIView
from django.db import transaction, close_old_connections
from django.shortcuts import get_object_or_404, render
import datetime
from django.utils import timezone
from django.db.models.functions import Concat
from django.db.models import Value
from django.contrib.gis import geos

import requests, os, boto3, random, string, time

from exponent_server_sdk import DeviceNotRegisteredError
from exponent_server_sdk import PushClient
from exponent_server_sdk import PushMessage
from exponent_server_sdk import PushResponseError
from exponent_server_sdk import PushServerError
from requests.exceptions import ConnectionError
from requests.exceptions import HTTPError

from joinMe.models import Friendship, Profile, Avatar, Event, Video, GuestToEvent, Place, Notification, UserGroup, Comment
from joinMe.serializers import UserGroupSerializer, UserGroupListSerializer, CommentSerializer

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

close_old_connections()


def time_stamp(myTime):
    return int(time.mktime(myTime.timetuple()) * 1000)


# Basic arguments. You should extend this function with the push features you
# want to use, or simply pass in a `PushMessage` object.
def send_push_message(token, message, extra=None, title=None, badge=0):
    try:
        response = PushClient().publish(
            PushMessage(to=token,
                        title=title,
                        body=message,
                        data=extra,
                        badge=badge))
    except PushServerError as exc:
        pass
    except (ConnectionError, HTTPError) as exc:
        pass

    try:
        # We got a response back, but we don't know whether it's an error yet.
        # This call raises errors so we can handle them with normal exception
        # flows.
        response.validate_response()
    except DeviceNotRegisteredError:
        pass
    except PushResponseError as exc:
        pass


def send_push_notification(user, message, body=None, title=None):
    if hasattr(user, 'profile') and user.profile.notification_key != "":
        now = timezone.now()
        badge = len(user.notifications.filter(event__ending_time__gte=now, state=0))
        send_push_message(user.profile.notification_key, message, body, title, badge)


def get_facebook_friends(user):
    response = requests.get('https://graph.facebook.com/me/friends', params=user.social_auth.get(provider="facebook").extra_data)

    if response.status_code == 200:
        ids_list = []
        for friend in response.json()["data"]:
            ids_list.append(friend['id'])

        # for friend in friends:
        #     friendship = Friendship(creator=user, friend=friend, state=1)
        #     friendship.save()

        friends = User.objects.filter(social_auth__uid__in=ids_list)
        return friends


# TODO: Add try and catch and test ...
class FirstConnection(APIView):

    def get(self, request, format=None):

        s3 = boto3.resource('s3')
        S3_BUCKET = os.environ.get('S3_BUCKET')

        if request.auth:
            user = request.user
            print(user)
            if len(Profile.objects.filter(user__pk=user.pk)) == 0 or not user.profile.init:

                # Get the avatar url of the user and store it
                # TODO: Check if the avatar already exist
                response = requests.get(
                    'https://graph.facebook.com/me/picture',
                    params={'access_token': user.social_auth.get(provider="facebook").extra_data['access_token'],
                            'type': 'large',
                            }
                )

                if response.status_code == 200:
                    hash_key = str(time.time()*100).split('.')[0].join([random.choice(string.ascii_letters + string.digits) for _ in range(4)])
                    key = 'avatar/avatar_' + hash_key + '.jpg'
                    url = 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, key)

                    s3_response = s3.Bucket(S3_BUCKET).put_object(ACL='public-read', Key=key, Body=response.content)

                    if response.status_code == 200:
                        # return Response(user.avatars.all()[0].url)
                        # Create a new avatar object with the facebook url
                        avatar = Avatar(url=url, user=user)
                        avatar.save()

                profile = Profile(user=request.user, init=True)
                profile.save()

            ctx = {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'avatar': user.avatars.last().url if user.avatars and user.avatars.last() else '',
            }

            return Response(ctx)

        return Response({'init': True})

    def post(self, request):
        if request.auth:
            user = request.user

            if 'notification_key' in request.data:
                user.profile.notification_key = request.data['notification_key']
                user.profile.save()

                return Response({"notification": True})

        return Response({"notification": False})


class Me(APIView):

    def get(self, request):
        if request.auth:
            user = request.user
            ctx = {
                'id': user.pk,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'avatar': user.avatars.last().url if user.avatars and user.avatars.last() else '',
            }
            return Response(ctx)
        return Response({'error': 'User not connected'})


class Users(APIView):

    def get(self, request):
        if request.auth:
            me = request.user
            users = User.objects.all().order_by('last_name')
            facebook_friends = get_facebook_friends(me)
            filtered = request.query_params.get('filter', '').replace('?', '')
            search = request.query_params.get('search', '').replace('?', '')
            if search != '':
                queryset = users.annotate(fullname=Concat('first_name', Value(' '), 'last_name'))
                users = queryset.filter(fullname__icontains=search)
                ff_queryset = facebook_friends.annotate(fullname=Concat('first_name', Value(' '), 'last_name'))
                facebook_friends = ff_queryset.filter(fullname__icontains=search)

            if filtered == 'no-friends':  # TODO: the ? is automatically added at the end of the url. Will have to debug that
                from django.db.models import Q
                users = users.filter(~Q(Q(friendship_creator__friend=me) | Q(friendship_friend__creator=me)))

            ctx = {'users': [], 'alpha_sorted_user': {}, 'facebook_friends': []}
            for user in users:
                if user.username != "admin" and me != user:
                    new_user = {
                        'id': user.pk,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'avatar': user.avatars.last().url if user.avatars and user.avatars.last() else '',
                        'is_friend': True if user.friendship_creator.filter(friend=me, state=1).first() or user.friendship_friend.filter(creator=me, state=1).first() else False
                    }
                    ctx['users'].append(new_user)
                    if user.first_name[0]:
                        if user.first_name[0].lower() not in ctx['alpha_sorted_user']:
                            ctx['alpha_sorted_user'][user.first_name[0].lower()] = []
                        ctx['alpha_sorted_user'][user.first_name[0].lower()].append(new_user)
            for user in facebook_friends:
                if user.username != "admin" and me != user:
                    new_user = {
                        'id': user.pk,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'avatar': user.avatars.last().url if user.avatars and user.avatars.last() else '',
                        'is_friend': True if user.friendship_creator.filter(friend=me, state=1).first() or user.friendship_friend.filter(creator=me, state=1).first() else False
                    }
                    ctx['facebook_friends'].append(new_user)

            return Response(ctx)


class UserGroupEndPoint(viewsets.ModelViewSet):

    serializer_class = UserGroupSerializer
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'update' or self.action == 'partial_update':
            return UserGroupListSerializer
        else:
            return UserGroupSerializer


    def get_queryset(self):
        user = self.request.user
        return user.friends_groups.all()

    def perform_create(self, serializer):
        users = self.request.data.get('users', None)
        users.append(self.request.user.pk)
        serializer.save(created_by=self.request.user, users=users)


class CommentEndPoint(viewsets.ModelViewSet):

    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return user.event_comments.all()

    def perform_create(self, serializer):
        user = self.request.user
        instance = serializer.save(created_by=self.request.user)

        from django.db.models import Q
        guests = GuestToEvent.objects.filter(Q(event=instance.event, state=0) | Q(event=instance.event, state=1))
        is_event_owner = user == instance.event.created_by
        for guest in guests:
            f_user = guest.guest
            if f_user == user:
                continue
            message = "%s: %s" % (user.first_name, instance.message)
            title = "%s's event" % instance.event.created_by.first_name

            send_push_notification(f_user, message, {'screen': 'event', 'event_id': instance.event.pk}, title)

        if not is_event_owner:
            message = "%s: %s" % (user.first_name, instance.message)
            send_push_notification(instance.event.created_by, message, {'screen': 'event', 'event_id': instance.event.pk}, 'Your event')




class EventList(APIView):

    def post(self, request):
        # TODO: convert mov file to mp4
        print("Starting to process the video upload ...")
        if request.auth:
            user = request.user
            data = request.data
            placeData = {'formatted_address': '', 'place_id': '', 'longitude': '', 'latitude': ''}
            duration = datetime.timedelta(hours=3)

            if 'place' in data:
                placeData = data['place']

            if 'duration' in data:
                duration = datetime.timedelta(hours=int(data['duration']['hours']), minutes=int(data['duration']['minutes']))

            if 'video' in data:
                with transaction.atomic():
                    url = data['video'].replace('/input/', '/output/').rsplit('.', 1)[0]+".mp4"

                    video = Video(video=url)
                    video.save()

                    is_public = True if 'public' in data and data['public'] else False

                    event = Event(created_by=user, duration=duration, ending_time=timezone.now()+duration, is_public=is_public)
                    event.save()
                    event.videos.set([video])
                    event.save()

                    place = Place(formatted_address=placeData.get('formatted_address', ''),
                                  place_id=placeData.get('place_id', ''), event=event)

                    longitude = placeData.get('longitude', '')
                    latitude = placeData.get('latitude', '')
                    if longitude != '' and latitude != '':
                        point = "POINT(%s %s)" % (longitude, latitude)
                        location = geos.fromstr(point)
                        place.location = location

                    place.save()

                    if 'friends' in data:
                        for f in data['friends']:
                            f_user = User.objects.filter(pk=f['id']).first()
                            if f_user and f_user != user:
                                send_push_notification(f_user,  "%s invited you to an event." % user.first_name, {'screen': 'event', 'event_id': event.pk})
                                channel_layer = get_channel_layer()
                                user_group_name = 'user_%s' % f_user.pk
                                async_to_sync(channel_layer.group_send)(user_group_name, {
                                    "type": "notifs.change",
                                    "action": "add",
                                    "quantity": 1
                                })
                                sharing = GuestToEvent(guest=f_user, event=event, state=0)
                                sharing.save()
                                notification = Notification(user=f_user, event=event, type_of_notification=0)
                                notification.save()

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
            coming = request.query_params.get('coming', '').replace('?', '')

            my_events = user.my_events.filter(ending_time__gte=now)
            events = Event.objects.filter(ending_time__gte=now, guests__guest=user).distinct()
            public_events = []

            if coming != '':
                events = events.filter(guests__state=1)
                print('Get only coming events')
            else:
                my_events = my_events.filter(is_public=False)
                events = events.filter(is_public=False)

            notifications = user.notifications.filter(event__ending_time__gte=now, state=0)

            ctx = {'notifications': len(notifications), 'my_events': [], 'events': [], 'public_events': []}

            #longitude = request.query_params.get('longitude', '').replace('?', '')
            #latitude = request.query_params.get('latitude', '').replace('?', '')

            #if longitude != '' and latitude != '':
            #    my_position = GEOSGeometry('POINT(%s %s)' % (longitude, latitude), srid=4326)
            #    public_events = Event.objects.filter(ending_time__gte=now,
            #                                         is_public=True,
            #                                         place__location__distance_lte=(my_position, D(km=50))).distinct()\
            #        .annotate(distance=Distance('place__location', my_position)).order_by('distance')

            public_events = Event.objects.filter(ending_time__gte=now, is_public=True).distinct()


            for my_event in my_events:
                video_url = my_event.videos.values_list('video', flat=True).all()
                thumb_url_splitted = video_url[0].rsplit('/', 1)
                thumb_url = thumb_url_splitted[0] + '/thumb-' + thumb_url_splitted[1].replace('.mp4', '-00001.png')
                guests = my_event.guests.all()

                event_notif = notifications.filter(event=my_event)
                new_event = {
                    'id': my_event.pk,
                    'is_public': my_event.is_public,
                    'is_mine': True,
                    'creator': {
                        'url': my_event.created_by.avatars.last().url,
                        'first_name': my_event.created_by.first_name,
                        'last_name': my_event.created_by.last_name
                    },
                    'coming': 3,
                    'creation_date': my_event.created,
                    'ending_time': my_event.ending_time,
                    'video_url': video_url,
                    'thumb_url': thumb_url,
                    'notifications': [{'type': notif.type_of_notification} for notif in event_notif],
                    'guests': [],
                }

                for guest in guests:
                    new_guest = {
                        'first_name': guest.guest.first_name,
                        'last_name': guest.guest.last_name,
                        'state': guest.state,
                        'avatar': guest.guest.avatars.last().url if guest.guest.avatars.last() else "",
                        'id': guest.guest.pk,
                    }
                    if new_guest not in new_event['guests']:
                        new_event['guests'].append(new_guest)

                ctx['my_events'].append(new_event)

            for event in events:
                video_url = event.videos.values_list('video', flat=True).all()
                thumb_url_splitted = video_url[0].rsplit('/', 1)
                thumb_url = thumb_url_splitted[0] + '/thumb-' + thumb_url_splitted[1].replace('.mp4', '-00001.png')

                guests = event.guests.all()

                event_notif = notifications.filter(event=event)
                new_event = {
                    'id': event.pk,
                    'is_public': event.is_public,
                    'is_mine': False,
                    'creator': {
                        'url': event.created_by.avatars.last().url,
                        'first_name': event.created_by.first_name,
                        'last_name': event.created_by.last_name
                    },
                    'coming': event.guests.filter(guest=user).first().state,
                    'creation_date': event.created,
                    'ending_time': event.ending_time,
                    'video_url': video_url,
                    'thumb_url': thumb_url,
                    'notifications': [{'type': notif.type_of_notification} for notif in event_notif],
                    'guests': [],
                }

                for guest in guests:
                    new_guest = {
                        'first_name': guest.guest.first_name,
                        'last_name': guest.guest.last_name,
                        'state': guest.state,
                        'avatar': guest.guest.avatars.last().url if guest.guest.avatars.last() else "",
                        'id': guest.guest.pk,
                    }
                    if new_guest not in new_event['guests']:
                        new_event['guests'].append(new_guest)

                ctx['events'].append(new_event)

            for event in public_events:
                video_url = event.videos.values_list('video', flat=True).all()
                thumb_url_splitted = video_url[0].rsplit('/', 1)
                thumb_url = thumb_url_splitted[0] + '/thumb-' + thumb_url_splitted[1].replace('.mp4', '-00001.png')

                guests = event.guests.all()

                event_notif = notifications.filter(event=event)
                new_event = {
                    'id': event.pk,
                    'is_public': event.is_public,
                    'is_mine': (event.created_by == user),
                    'creator': {
                        'url': event.created_by.avatars.last().url,
                        'first_name': event.created_by.first_name,
                        'last_name': event.created_by.last_name
                    },
                    'coming': event.guests.filter(guest=user).first().state if event.guests.filter(guest=user).first() else 0,
                    'creation_date': event.created,
                    'ending_time': event.ending_time,
                    'video_url': video_url,
                    'thumb_url': thumb_url,
                    'notifications': [{'type': notif.type_of_notification} for notif in event_notif],
                    'guests': [],
                    #'distance': event.distance.km,
                }

                for guest in guests:
                    new_guest = {
                        'first_name': guest.guest.first_name,
                        'last_name': guest.guest.last_name,
                        'state': guest.state,
                        'avatar': guest.guest.avatars.last().url if guest.guest.avatars.last() else "",
                        'id': guest.guest.pk,
                    }
                    if new_guest not in new_event['guests']:
                        new_event['guests'].append(new_guest)

                ctx['public_events'].append(new_event)

            return Response(ctx)

        return Response({'response': request.auth})


class EventDetailsForWeb(APIView):

    permission_classes = []

    def get(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)

        video_url = event.videos.last().video
        video_url_webm = video_url.replace('.mp4', '.gif')

        ctx = {
            'video_url': video_url,
            'video_thumb_url': video_url_webm,
            'creation_date': event.created,
            'id': event.pk,
            'place': {
                'formatted_address': event.place.last().formatted_address,
                'place_id': event.place.last().place_id,
            },
            'ending_date': event.ending_time,
        }

        return render(request, 'events.html', ctx)


class EventDetails(APIView):
    # TODO: return the event info
    def get(self, request, event_id):
        if request.auth:
            user = request.user

            event = get_object_or_404(Event, pk=event_id)
            guests = event.guests.all()
            notifications = user.notifications.filter(event=event)
            comments = Comment.objects.filter(event=event)
            video_url = event.videos.values_list('video', flat=True).all()
            thumb_url_splitted = video_url[0].rsplit('/', 1)
            thumb_url = thumb_url_splitted[0] + '/thumb-' + thumb_url_splitted[1].replace('.mp4', '-00001.png')

            ctx = {
                'video_url': video_url,
                'thumb_url': thumb_url,
                'creation_date': event.created,
                'id': event.pk,
                'creator': {
                    'is_me': event.created_by.pk == user.pk,
                    'id': event.created_by.pk,
                    'first_name': event.created_by.first_name,
                    'last_name': event.created_by.last_name,
                    'avatar': event.created_by.avatars.last().url,
                    'state': 1,     # The creator is always coming
                    'comment': (comments.filter(created_by=event.created_by).last().message if comments.filter(created_by=event.created_by).last() else '')
                },
                'place': {
                    'formatted_address': event.place.last().formatted_address,
                    'place_id': event.place.last().place_id,
                },
                'ending_date': event.ending_time,
                'notifications': [{
                    'type': notif.type_of_notification
                } for notif in notifications],
                'guests': [],
            }

            notifications.delete()

            for guest in guests:
                new_guest = {
                    'first_name': guest.guest.first_name,
                    'last_name': guest.guest.last_name,
                    'state': guest.state,
                    'avatar': guest.guest.avatars.last().url if guest.guest.avatars.last() else "",
                    'id': guest.guest.pk,
                    'comment': (comments.filter(created_by=guest.guest).last().message if comments.filter(created_by=guest.guest).last() else ''),
                }
                if new_guest not in ctx['guests']:
                    ctx['guests'].append(new_guest)

            return Response(ctx)

        return Response({'response': request.auth})

    def delete(self, request, event_id):
        if request.auth:
            user = request.user
            event = Event.objects.filter(pk=event_id, created_by=user).first()
            event.delete()
            return Response({'message': 'Event deleted'})
        return Response({'message': 'Authentication denied'})



    def put(self, request, event_id):
        if request.auth:
            user = request.user
            data = request.data

            if 'coming' in data:

                event = get_object_or_404(Event, pk=event_id)
                g = event.guests.filter(guest=user).first()

                if g and not event.is_public:
                    g.state = data['coming']
                    g.save()

                    channel_layer = get_channel_layer()
                    event_group_name = 'event_%s' % event_id
                    async_to_sync(channel_layer.group_send)(event_group_name, {
                        "type": "status.change",
                        "guest_id": user.pk,
                        "new_status": data['coming']
                    })

                    from django.db.models import Q
                    guests = GuestToEvent.objects.filter(Q(event=event, state=0) | Q(event=event, state=1))
                    for guest in guests:
                        f_user = guest.guest
                        if g.event.created_by != f_user and f_user != user and data['coming'] == 1:
                            print("send notif to %s" % f_user.first_name)
                            user_group_name = 'user_%s' % f_user.pk
                            async_to_sync(channel_layer.group_send)(user_group_name, {
                                "type": "notifs.change",
                                "action": "add",
                                "quantity": 1
                            })
                            notification = Notification(user=f_user, event=g.event, type_of_notification=1)
                            notification.save()

                            send_push_notification(f_user,  "%s is joining %s." % (g.guest.first_name, g.event.created_by.first_name), {'screen': 'event', 'event_id': g.event.pk})

                    if user != g.event.created_by and data['coming'] == 1:
                        print("send notif to %s" % g.event.created_by.first_name)
                        user_group_name = 'user_%s' % g.event.created_by.pk
                        async_to_sync(channel_layer.group_send)(user_group_name, {
                            "type": "notifs.change",
                            "action": "add",
                            "quantity": 1
                        })
                        notification = Notification(user=g.event.created_by, event=g.event, type_of_notification=1)
                        notification.save()
                        send_push_notification(g.event.created_by, "%s is joining you." % g.guest.first_name, {'screen': 'event', 'event_id': g.event.pk})

                    return Response({'message': 'Update your state to the event is done'})

                elif event.is_public:

                    if g and data['coming'] == 2:
                        g.delete()
                        channel_layer = get_channel_layer()
                        event_group_name = 'event_%s' % event_id
                        async_to_sync(channel_layer.group_send)(event_group_name, {
                            "type": "guests.change",
                            "action": "delete",
                            "guest": {
                                "id": user.pk,
                            },
                        })
                    elif data['coming'] == 1:
                        if not g:
                            g = GuestToEvent(guest=user, event=event, state=data['coming'])
                            channel_layer = get_channel_layer()
                            event_group_name = 'event_%s' % event_id
                            async_to_sync(channel_layer.group_send)(event_group_name, {
                                "type": "guests.change",
                                "action": "add",
                                "guest": {
                                    "id": user.pk,
                                    "first_name": user.first_name,
                                    "last_name": user.last_name,
                                    "avatar": user.avatars.last().url if user.avatars and user.avatars.last() else '',
                                    "state": 1,
                                    "comment": "",
                                },
                            })
                        else:
                            g.state = data['coming']
                            channel_layer = get_channel_layer()
                            event_group_name = 'event_%s' % event_id
                            async_to_sync(channel_layer.group_send)(event_group_name, {
                                "type": "status.change",
                                "guest_id": user.pk,
                                "new_status": data['coming']
                            })
                        g.save()

                else:
                    return Response({'message': 'You\'re not invited to this event'})

            return Response({'message': 'Can\'t find coming variable'})

        return Response({'response': request.auth})


class VideoEvent(APIView):

    def post(self, request, event_id):

        if request.auth:
            user = request.user
            data = request.data
            event = get_object_or_404(Event, pk=event_id)

            if event and 'video' in data:
                with transaction.atomic():
                    url = data['video'].replace('/input/', '/output/').rsplit('.', 1)[0]+".mp4"

                    video = Video(video=url, event=event)
                    video.save()

                from django.db.models import Q
                guests = GuestToEvent.objects.filter(Q(event=event, state=1) | Q(event=event, state=0))
                is_event_owner = (user == event.created_by)
                for guest in guests:
                    f_user = guest.guest
                    if f_user == user:
                        continue
                    message = "%s added a new video" % user.first_name if is_event_owner else \
                        "%s added a video to %s'event" % (user.first_name, event.created_by.first_name)

                    send_push_notification(f_user, message, {'screen': 'event', 'event_id': event.pk})

                if not is_event_owner:
                    send_push_notification(event.created_by, "%s added a new video to your event" % user.first_name, {'screen': 'event', 'event_id': event.pk})

                return Response({"message": "Video added to the event"})
            return Response({"message": "You need to put a video url in 'video'"})
        return Response({"message": "You're not authenticated"})


class FriendList(APIView):

    def get(self, request):
        if request.auth:
            user = request.user
            event_id = int(request.query_params.get('event_id', '-1?').replace('?', ''))
            event = Event.objects.filter(pk=event_id).first()

            from django.db.models import Q

            friends = User.objects.distinct().filter(Q(friendship_creator__friend__pk=user.pk, friendship_creator__state=1) |
                                          Q(friendship_friend__creator__pk=user.pk, friendship_friend__state=1)).order_by('last_name')

            if event:
                list_of_participants = list(event.guests.all().values_list('guest__pk', flat=True))
                list_of_participants.append(event.created_by.pk)
                friends = friends.exclude(pk__in=list_of_participants)

            ctx = {'friends': []}
            for friend in friends:
                new_friend = {
                    'id': friend.pk,
                    'first_name': friend.first_name,
                    'last_name': friend.last_name,
                    'avatar': friend.avatars.last().url if friend.avatars and friend.avatars.last() else '',
                }
                ctx['friends'].append(new_friend)

            return Response(ctx)

        return Response({'response': request.auth})

    def post(self, request):
        if request.auth:
            user = request.user
            if request.data['friend_id']:
                friend = User.objects.filter(pk=request.data['friend_id']).first()
                if friend:
                    from django.db.models import Q
                    alreadyExist = Friendship.objects.filter(Q(creator=user, friend=friend) | Q(creator=friend, friend=user)).first()
                    if not alreadyExist:
                        friendship = Friendship(creator=user, friend=friend, state=1)
                        friendship.save()
                        send_push_notification(friend.profile.notification_key, "You and %s are now friends." % (user.first_name))

                    return Response({"message": "Done"})
                return Response({"error": "No friend found"})
            return Response({"error": "Need a friend_id"})
        return Response({"error": "You're not authentified"})


class FriendshipManager(APIView):

    def put(self, request, user_id):

        if request.auth:
            user = request.user
            data = request.data
            from django.db.models import Q
            friendship = get_object_or_404(Friendship, Q(creator__pk=user.pk, friend__pk=user_id) | Q(creator__pk=user_id, friend__pk=user.pk))

            if data['action'] == 'refuse':
                friendship.delete()

            elif data['action'] == 'block':
                friendship.state = 2
                friendship.save()

            return Response({"message": "Done"})


class SharingEvent(APIView):

    def put(self, request, event_id):

        if request.auth:
            user = request.user

            event = get_object_or_404(Event, pk=event_id)

            if event.created_by == user or event.guests.filter(guest_id=user.pk).first():

                for f in request.data['friends']:
                    f_user = User.objects.filter(pk=f['id']).first()
                    if f_user and f_user != event.created_by:
                        sharing = GuestToEvent(guest=f_user, event=event, state=0)
                        sharing.save()

                        channel_layer = get_channel_layer()
                        event_group_name = 'event_%s' % event_id
                        async_to_sync(channel_layer.group_send)(event_group_name, {
                            "type": "guests.change",
                            "action": "add",
                            "guest": {
                                "id": f_user.pk,
                                "first_name": f_user.first_name,
                                "last_name": f_user.last_name,
                                "avatar": f_user.avatars.last().url if f_user.avatars and f_user.avatars.last() else '',
                                "state": 0,
                                "comment": "",
                            },
                        })

                        user_group_name = 'user_%s' % f_user.pk
                        async_to_sync(channel_layer.group_send)(user_group_name, {
                            "type": "notifs.change",
                            "action": "add",
                            "quantity": 1
                        })

                        notification = Notification(user=f_user, event=event, type_of_notification=0)
                        notification.save()
                        send_push_notification(f_user.profile.notification_key, "%s invited you to %s'event." % (user.first_name, event.created_by.first_name))

            ctx = {'response': []}
            guests = [gte.guest for gte in GuestToEvent.objects.filter(event__pk=event.pk)]

            for guest in guests:
                new_guest = {
                    'name': guest.last_name,
                }
                ctx['response'].append(new_guest)

            return Response(ctx)

        return Response({'response': request.auth})


class Notifications(APIView):

    def get(self, request):
        if request.auth:
            user = request.user
            notifications = user.notifications
            return Response({notifications: notifications})
        return Response({'response': "can't find notifications"})

    def put(self, request, notif_id, notif_group):
        if request.auth:
            user = request.user
            notif_id = request.data["notif_id"]
            notif_group = request.data["notif_group"]
            if notif_group:
                if notif_group == 'new':
                    notifications = user.notifications.filter(type_of_notification=0, state=0)
                    for notification in notifications:
                        notification.state = 1
                        notification.save()
                elif notif_group == 'coming':
                    notifications = user.notifications.filter(type_of_notification=1, state=0)
                    for notification in notifications:
                        notification.state = 1
                        notification.save()
                elif notif_group == 'all':
                    notifications = user.notifications.filter(state=0)
                    for notification in notifications:
                        notification.state = 1
                        notification.save()
            else:
                notification = user.notifications.filter(pk=notif_id)
                notification.state = 1
                notification.save()

            return Response({'response': "done"})

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
