from channels.generic.websocket import WebsocketConsumer
import json
from asgiref.sync import async_to_sync


class EventConsumer(WebsocketConsumer):
    def connect(self):
        self.event_id = self.scope['url_route']['kwargs']['event_id']
        self.event_group_name = 'event_%s' % self.event_id

        async_to_sync(self.channel_layer.group_add)(self.event_group_name, self.channel_name)

        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)("chat", self.channel_name)

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        self.send(text_data=json.dumps({
            'message': message
        }))

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

