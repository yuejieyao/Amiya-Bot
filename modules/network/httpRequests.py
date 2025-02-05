import os
import json
import requests

from modules.network.chainBuilder import Chain
from modules.config import get_config

session_file = 'temp/session.txt'


class HttpRequests:
    def __init__(self):
        self.request = requests.session()
        self.config = get_config()

    def url(self, interface):
        return 'http://%s:%d/%s' % (self.config['server']['server_ip'], self.config['server']['http_port'], interface)

    def post(self, interface, data):
        response = self.request.post(self.url(interface), data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        if response.status_code == 200:
            return json.loads(response.text)
        return False

    def get(self, interface):
        response = self.request.get(self.url(interface))
        if response.status_code == 200:
            return json.loads(response.text)
        return False

    def init_session(self):
        response = self.post('verify', {'verifyKey': self.config['server']['auth_key']})
        session = response['session']
        self_id = get_config('self_id')

        session_record = self.get_session()
        if session_record:
            self.post('release', {'sessionKey': session_record, 'qq': self_id})

        self.post('bind', {'sessionKey': session, 'qq': self_id})

        with open(session_file, mode='w+') as session_record:
            session_record.write(session)

    @staticmethod
    def get_session():
        if os.path.exists(session_file):
            with open(session_file, mode='r+') as session_record:
                session = session_record.read()
                if session:
                    return session
        return ''

    def get_group_list(self):
        session = self.get_session()
        if self.config['close_beta']['enable']:
            return [{
                'id': self.config['close_beta']['group_id']
            }]
        else:
            response = self.get('groupList?sessionKey=%s' % session)
            if response and response['code'] == 0:
                group_list = {}
                for item in response['data']:
                    if item['id'] not in group_list:
                        group_list[item['id']] = item
                group_list = [n for i, n in group_list.items()]
                return group_list
            return []

    def handle_join_group(self, data, operate):
        self.post('/resp/botInvitedJoinGroupRequestEvent', {
            'sessionKey': self.get_session(),
            'eventId': data['eventId'],
            'fromId': data['fromId'],
            'groupId': data['groupId'],
            'operate': 1 if operate else 0,
            'message': ''
        })

    def leave_group(self, group_id, flag=True):
        if flag:
            session = self.get_session()
            self.post('quit', {'sessionKey': session, 'target': group_id})

    def send_message(self, data, message='', message_chain=None, at=False):
        session = self.get_session()
        command, content = Chain(session, data, message, message_chain, at).content()

        self.post(command, content)

    def send_to_admin(self, text):
        self.send_message({'user_id': get_config('admin_id'), 'type': 'friend'}, text)
