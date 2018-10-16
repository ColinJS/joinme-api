from channels.generic.websocket import WebsocketConsumer
import json
from asgiref.sync import async_to_sync
from oauth2_provider.models import AccessToken
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from joinMe.models import Notification


def userByToken(token):
    user_token = AccessToken.objects.filter(token=token).first()
    close_old_connections()
    if user_token:
        user = user_token.user
        return user
    else:
        return AnonymousUser()


class EventConsumer(WebsocketConsumer):
    def connect(self):
        self.event_id = self.scope['url_route']['kwargs']['event_id']
        self.event_group_name = 'event_%s' % self.event_id
        self.user = userByToken(self.scope['url_route']['kwargs']['token'])
        if self.user and self.user != AnonymousUser:
            async_to_sync(self.channel_layer.group_add)(self.event_group_name, self.channel_name)

            self.accept()
        else:
            self.accept()
            self.close()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.event_group_name, self.channel_name)

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json['action']
        if action == 'delete_notifs':
            event_notifs = Notification.objects.filter(event__pk=self.event_id, user__pk=self.user.pk)
            notifs_len = len(event_notifs)
            event_notifs.delete()

            async_to_sync(self.channel_layer.group_send)('user_%s' % self.user.pk, {
                'type': 'notifs_change',
                'action': 'delete',
                'quantity': notifs_len,
            })

    def status_change(self, event):
        guest_id = event['guest_id']
        new_status = event['new_status']

        self.send(text_data=json.dumps({
            'type': 'status_change',
            'guest_id': guest_id,
            'new_status': new_status
        }))

    def guests_change(self, event):
        action = event['action']
        guest = event['guest']

        self.send(text_data=json.dumps({
            'type': 'guest_'+action,
            'guest': guest
        }))


class UserConsumer(WebsocketConsumer):

    def connect(self):
        self.user = userByToken(self.scope['url_route']['kwargs']['token'])
        if self.user and self.user != AnonymousUser:
            self.user_group_name = 'user_%s' % self.user.pk

            async_to_sync(self.channel_layer.group_add)(self.user_group_name, self.channel_name)

            self.accept()

        else:
            self.accept()
            self.close()

    def receive(self, text_data):
        text_data_json = json.loads(text_data)

        self.send(text_data=json.dumps({
            'first_name': self.user.first_name,
            'message': text_data
        }))

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.user_group_name, self.channel_name)

    def notifs_change(self, event):
        action = event['action']
        number = event['quantity']
        self.send(text_data=json.dumps({
            'type': 'notifs_'+action,
            'quantity': number
        }))
