from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404, render
import datetime
from django.utils import timezone

import requests, os, boto3, random, string, time

from exponent_server_sdk import DeviceNotRegisteredError
from exponent_server_sdk import PushClient
from exponent_server_sdk import PushMessage
from exponent_server_sdk import PushResponseError
from exponent_server_sdk import PushServerError
from requests.exceptions import ConnectionError
from requests.exceptions import HTTPError

from joinMe.models import Friendship, Profile, Avatar, Event, Video, GuestToEvent, Place, Notification


# Basic arguments. You should extend this function with the push features you
# want to use, or simply pass in a `PushMessage` object.
def send_push_message(token, message, extra=None):
    try:
        response = PushClient().publish(
            PushMessage(to=token,
                        body=message,
                        data=extra))
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

                print(response)
                if response.status_code == 200:
                    hash_key = str(time.time()*100).split('.')[0].join([random.choice(string.ascii_letters + string.digits) for _ in range(4)])
                    key = 'avatar/avatar_' + hash_key + '.jpg'
                    url = 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, key)

                    s3_response = s3.Bucket(S3_BUCKET).put_object(ACL='public-read', Key=key, Body=response.content)

                    print(s3_response)

                    if response.status_code == 200:
                        # return Response(user.avatars.all()[0].url)
                        # Create a new avatar object with the facebook url
                        avatar = Avatar(url=url, user=user)
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
                        new_friends = User.objects.filter(social_auth__uid=friend['id']).first()
                        if new_friends:
                            friends.append(new_friends)

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

    def post(self, request):
        if request.auth:
            user = request.user

            if 'notification_key' in request.data:
                if user.profile.notification_key == "":
                    user.profile.notification_key = request.data['notification_key']
                    user.profile.save()

                return Response({"notification": True})

        return Response({"notification": False})


class Me(APIView):

    def get(self, request):
        if request.auth:
            user = request.user
            ctx = {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'avatar': user.avatars.last().url,
            }
            return Response(ctx)
        return Response({'error': 'User not connected'})


class Users(APIView):

    def get(self, request):
        if request.auth:
            me = request.user
            users = User.objects.all()
            filtered = request.query_params.get('filter', '')
            print(request.query_params)
            print(filtered)
            if filtered == 'no-friends?':  # TODO: the ? is automatically added at the end of the url. Will have to debug that
                from django.db.models import Q
                users = users.filter(~Q(Q(friendship_creator__friend=me, friendship_creator__state=1) |
                                        Q(friendship_friend__creator=me, friendship_friend__state=1)))

            ctx = {'users': []}
            for user in users:
                if user.username != "admin" and me != user:
                    new_user = {
                        'id': user.pk,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'avatar': user.avatars.last().url if user.avatars and user.avatars.last() else '',
                    }
                    ctx['users'].append(new_user)

            return Response(ctx)


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
                    url = data['video'].replace('/input/', '/output/').rsplit('.', 1)[0]+".mp4"

                    video = Video(video=url)
                    video.save()

                    event = Event(created_by=user, duration=duration, ending_time=timezone.now()+duration)
                    event.save()
                    event.videos.set([video])
                    event.save()

                    place = Place(formatted_address=place.get('formatted_address', ''), place_id=place.get('place_id', ''),event=event)
                    place.save()

                    if 'public' in data and data['public']:
                        users = User.objects.all()
                        for f_user in users:
                            if f_user != user and f_user.pk != 1:
                                if f_user.profile.notification_key != "":
                                    send_push_message(f_user.profile.notification_key, "%s invited you to an event." % (user.first_name))
                                notification = Notification(user=f_user, event=event, type_of_notification=0)
                                notification.save()
                                sharing = GuestToEvent(guest=f_user, event=event, state=0)
                                sharing.save()

                    elif 'friends' in data:
                        for f in data['friends']:
                            f_user = User.objects.filter(pk=f['id']).first()
                            if f_user:
                                if f_user.profile.notification_key != "":
                                    send_push_message(f_user.profile.notification_key, "%s invited you to an event." % (user.first_name))
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

            my_events = user.my_events.filter(ending_time__gte=now)
            events = []
            notifications = user.notifications.filter(state=0)

            for e in user.events.all():
                if e.event not in events and e.event.ending_time >= now:
                    events.append(e.event)

            ctx = {'notifications': len(notifications), 'my_events': [], 'events': []}

            for my_event in my_events:
                event_notif = notifications.filter(event=my_event)
                new_event = {
                    'id': my_event.pk,
                    'creator': {
                        'url': my_event.created_by.avatars.last().url,
                        'first_name': my_event.created_by.first_name,
                        'last_name': my_event.created_by.last_name
                    },
                    'creation_date': my_event.created,
                    'ending_time': my_event.ending_time,
                    'video_url': my_event.videos.last().video,
                    'notifications': [{'type': notif.type_of_notification} for notif in event_notif]
                }
                ctx['my_events'].append(new_event)

            for event in events:
                event_notif = notifications.filter(event=event)
                new_event = {
                    'id': event.pk,
                    'creator': {
                        'url': event.created_by.avatars.last().url,
                        'first_name': event.created_by.first_name,
                        'last_name': event.created_by.last_name
                    },
                    'creation_date': event.created,
                    'ending_time': event.ending_time,
                    'video_url': event.videos.last().video,
                    'notifications': [{'type': notif.type_of_notification} for notif in event_notif]
                }
                ctx['events'].append(new_event)

            return Response(ctx)

        return Response({'response': request.auth})


class EventDetailsForWeb(APIView):

    permission_classes = []

    def get(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)

        video_url = event.videos.last().video
        video_url_webm = video_url.replace('.mp4', '.webm')

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
            notifications = user.notifications.filter(event=event, state=0)
            ctx = {
                'video_url': event.videos.last().video,
                'creation_date': event.created,
                'id': event.pk,
                'creator': {
                    'is_me': event.created_by.pk == user.pk,
                    'id': event.created_by.pk,
                    'first_name': event.created_by.first_name,
                    'last_name': event.created_by.last_name,
                    'avatar': event.created_by.avatars.last().url
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

            for guest in guests:
                new_guest = {
                    'first_name': guest.guest.first_name,
                    'last_name': guest.guest.last_name,
                    'state': guest.state,
                    'avatar': guest.guest.avatars.last().url if guest.guest.avatars.last() else "",
                    'id': guest.guest.pk,
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
                guestsToEvent = GuestToEvent.objects.filter(event__pk=event_id)
                guestToEvent = guestsToEvent.filter(guest__pk=user.pk)

                g = guestToEvent.first()
                if g:
                    g.state = data['coming']
                    g.save()

                    for guest in guestsToEvent:
                        f_user = guest.guest
                        if g.event.created_by != f_user and f_user != user and data['coming'] == 1:
                            print("send notif to %s" % f_user.first_name)
                            notification = Notification(user=f_user, event=g.event, type_of_notification=1)
                            notification.save()
                            if f_user.profile.notification_key != "":
                                send_push_message(f_user.profile.notification_key, "%s is joining %s" % (g.guest.first_name, g.event.created_by.first_name))

                    if user != g.event.created_by and data['coming'] == 1:
                        print("send notif to %s" % g.event.created_by.first_name)
                        notification = Notification(user=g.event.created_by, event=g.event, type_of_notification=1)
                        notification.save()
                        send_push_message(g.event.created_by.profile.notification_key, "%s is joining you" % g.guest.first_name)

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
                        if friend.profile.notification_key != "":
                            send_push_message(friend.profile.notification_key, "You and %s are friend now!" % (user.first_name))

                    return Response({"message": "Done"})
                return Response({"error": "No friend found"})
            return Response({"error": "Need a friend_id"})
        return Response({"error": "You're not authentified"})


class SharingEvent(APIView):

    def put(self, request, event_id):

        if request.auth:
            user = request.user

            event = get_object_or_404(Event, pk=event_id)

            if event.created_by == user or event.guests.filter(guest_id=user.pk).first():

                print('We get the event and we can add friends')
                print(request.data['friends'])

                for f in request.data['friends']:
                    f_user = User.objects.filter(pk=f['id']).first()
                    print(f_user)
                    if f_user:
                        sharing = GuestToEvent(guest=f_user, event=event, state=0)
                        sharing.save()
                        print(sharing)
                        notification = Notification(user=f_user, event=event, type_of_notification=0)
                        notification.save()
                        if f_user.profile.notification_key != "":
                            send_push_message(f_user.profile.notification_key, "%s invited you to an event." % (event.created_by.first_name))


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
