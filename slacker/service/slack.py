import cachetools
import logging
import requests
from ..sentinel import Sentinel
from .base import Agent, Channel, Notice, BaseService

LOG = logging.getLogger(__name__)


class Service(BaseService):
    IM_PLACEHOLDER = Sentinel("(im)")

    def __init__(self, *args, team=None, bot_oauth=None, user_oauth=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.bot = bot_oauth
        self.user = user_oauth
        self._user_cache = cachetools.TTLCache(maxsize=1024, ttl=600)
        self._channel_cache = cachetools.TTLCache(maxsize=1024, ttl=600)
        self.session = requests.Session()

    def get(self, *args, **kwargs):
        return self.session.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self.session.post(*args, **kwargs)

    @staticmethod
    def json(resp):
        j = resp.json()
        if resp.status_code != 200 or not j.get('ok'):
            raise RuntimeError(j.get('error'))
        return j

    def broadcast(self, channel=None, text=None):
        LOG.debug("Broadcasting to %s: %r", channel, text)
        resp = self.post('https://slack.com/api/chat.postMessage',
                         headers={'Authorization': 'Bearer {}'.format(self.bot)},
                         json={"text": str(text), "channel": channel.id})
        return self.json(resp)

    def new_channel(self, name=None, private=False, invite=None):
        LOG.debug("Constructing new channel: %s for %s", name, invite)

        resp = self.post('https://slack.com/api/conversations.create',
                         headers={'Authorization': 'Bearer {}'.format(self.user)},
                         json={'name': name, 'is_private': private, 'user_ids': [user.id for user in invite]})
        j = self.json(resp)

        channel = Channel(id=j.get('channel', {}).get('id'),
                          name=j.get('channel', {}).get('name'),
                          is_private=j.get('channel', {}).get('is_private', False))
        LOG.info("channel created: %s", channel)

        # Invite the users to the channel
        self.invite_to_channel(channel=channel, invite=invite)

        # The high-privileged user must leave the channel
        resp = self.post('https://slack.com/api/conversations.leave',
                         headers={'Authorization': 'Bearer {}'.format(self.user)},
                         json={'channel': channel.id})
        self.json(resp)

        return channel

    def delete_channel(self, channel=None):
        LOG.debug("Deleting channel: %s", channel)

        if channel.is_im:
            resp = self.post('https://slack.com/api/conversations.close',
                             headers={'Authorization': 'Bearer {}'.format(self.user)},
                             json={'channel': channel.id})
        elif channel.is_private:
            resp = self.post('https://slack.com/api/groups.delete',
                             headers={'Authorization': 'Bearer {}'.format(self.user)},
                             json={'channel': channel.id})
        else:
            resp = self.post('https://slack.com/api/channels.delete',
                             headers={'Authorization': 'Bearer {}'.format(self.user)},
                             json={'channel': channel.id})
        j = self.json(resp)
        LOG.debug("Channel delete responds with %s", j)

    def invite_to_channel(self, channel=None, invite=None):
        if invite is not None:
            resp = self.post('https://slack.com/api/conversations.invite',
                             headers={'Authorization': 'Bearer {}'.format(self.user)},
                             json={'channel': channel.id, 'users': ','.join(user.id for user in invite)})
            self.json(resp)
        return

    def lookup_channel(self, channel=None):
        LOG.debug("Looking up channel details: %s", channel)
        if channel.name is not None:
            return channel
        name = self._channel_cache.get(channel.id)
        if name is not None:
            channel = channel.replace(name=name)
            LOG.debug('Cache finds channel id %s with name %s', channel.id, channel.name)
            return channel
        # Do the lookup
        try:
            resp = self.get('https://slack.com/api/conversations.info',
                            params={'channel': channel.id},
                            headers={'Authorization': 'Bearer {}'.format(self.bot)})
            if resp.status_code == 200:
                j = resp.json()
                if j.get('ok'):
                    if j.get('channel', {}).get('is_im', False):
                        channel = channel.replace(name=Service.IM_PLACEHOLDER)
                    else:
                        channel = channel.replace(name=j.get('channel', {}).get('name'))
                    self._channel_cache[channel.id] = channel.name
                    LOG.debug('Cache records channel id %s with name %s', channel.id, channel.name)
                    return channel

        except Exception as e:
            LOG.error('Problem looking up channel name: %s', e)

        return channel

    def lookup_user(self, agent=None):
        LOG.debug("Looking up user details: %s", agent)
        if agent.name is not None:
            return agent
        cached = self._user_cache.get(agent.id)
        if cached is not None:
            LOG.debug('Cache finds agent id %s with %s', agent.id, cached)
            return cached
        # Do the lookup
        try:
            resp = self.get('https://slack.com/api/users.info',
                            params={'user': agent.id},
                            headers={'Authorization': 'Bearer {}'.format(self.bot)})
            if resp.status_code == 200:
                j = resp.json()
                if j.get('ok'):
                    agent = agent.replace(name=j.get('user', {}).get('name'),
                                          is_bot=j.get('user', {}).get('is_bot', False),
                                          real_name=j.get('user', {}).get('real_name', ""))

                    self._user_cache[agent.id] = agent
                    LOG.debug('Cache records agent id %s with %s', agent.id, agent)
                    return agent

        except Exception as e:
            LOG.error('Problem looking up user name: %s', e)

        return agent

    def post_notice(self, channel=None, notice=None, text=None):
        if notice is None:
            resp = self.broadcast(channel=channel, text=text)
            notice = Notice(channel, resp['ts'])
            resp = self.post('https://slack.com/api/pins.add',
                             headers={'Authorization': 'Bearer {}'.format(self.bot)},
                             json={"channel": channel.id, "timestamp": notice.id})
            self.json(resp)
            return notice

        assert channel == notice.channel

        LOG.debug("Updating notice to %s: %r", channel, text)
        resp = requests.post('https://slack.com/api/chat.update',
                             headers={'Authorization': 'Bearer {}'.format(self.bot)},
                             json={"text": str(text),
                                   "channel": channel.id,
                                   "ts": notice.id})
        self.json(resp)
        return notice

    def delete_message(self, channel=None, message_id=None):
        resp = requests.post('https://slack.com/api/chat.delete',
                             headers={'Authorization': 'Bearer {}'.format(self.user)},
                             json={"channel": channel.id,
                                   "ts": message_id})
        self.json(resp)

    def whisper(self, channel=None, agent=None, text=None):
        LOG.debug("Broadcasting to %s: %r", channel, text)
        resp = self.post('https://slack.com/api/chat.postEphemeral',
                         headers={'Authorization': 'Bearer {}'.format(self.bot)},
                         json={"text": str(text), "channel": channel.id, "user": agent.id})
        return self.json(resp)

