import functools
import logging
from ..sentinel import Sentinel
from .base import Agent, Channel, Notice, BaseService

LOG = logging.getLogger(__name__)


def delay(f):
    @functools.wraps(f)
    def eventually(self, *args, **kwargs):
        self.actions.append((f, args, kwargs))
    return eventually


class Service(BaseService):
    IM_PLACEHOLDER = Sentinel("(im)")

    def __init__(self, *args, delegate=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.delegate = delegate
        self.actions = []

    @delay
    def broadcast(self, channel=None, text=None):
        # If this channel was made in this txn, fully-resolve it
        channel = self.delegate.lookup_channel(channel=channel)
        return self.delegate.broadcast(channel=channel, text=text)

    def new_channel(self, name=None, private=False, invite=None):
        channel = Channel(name=name, is_private=private)
        self.actions.append((self._new_channel, (channel,), {}))
        self.invite_to_channel(channel=channel, invite=invite)
        return channel

    def _new_channel(self, channel):
        # Resolve the channel if possible
        channel = self.delegate.lookup_channel(channel=channel)
        if channel.id is None:
            channel = self.delegate.new_channel(name=channel.name, private=channel.is_private)

    @delay
    def delete_channel(self, channel=None):
        self.delegate.delete_channel(channel=channel)

    @delay
    def invite_to_channel(self, channel=None, invite=None):
        channel = self.delegate.lookup_channel(channel=channel)
        if invite is not None:
            invite = [self.delegate.lookup_user(user) for user in invite]
            self.delegate.invite_to_channel(channel=channel, invite=invite)

    def lookup_channel(self, channel=None):
        if channel.id is not None:
            # We might want to look up the channel name
            return self.delegate.lookup_channel(channel=channel)
        return channel

    def lookup_user(self, agent=None):
        # Might as well do this immediately
        return self.delegate.lookup_user(agent=agent)

    def post_notice(self, channel=None, notice=None, text=None):
        return None

    @delay
    def delete_message(self, channel=None, message_id=None):
        channel = self.delegate.lookup_channel(channel=channel)
        self.delegate.delete_message(channel=channel, message_id=message_id)

    @delay
    def whisper(self, channel=None, agent=None, text=None):
        channel = self.delegate.lookup_channel(channel=channel)
        agent = self.delegate.lookup_agent(agent=agent)
        return self.delegate.whisper(channel=channel, agent=agent, text=text)

    def commit(self):
        for action, args, kwargs in self.actions:
            action(*args, **kwargs)
