from collections import namedtuple


class Channel:
    def __init__(self, id=None, name=None, is_private=False, is_im=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id
        self.name = name
        self.is_private = is_private
        self.is_im = is_im

    def replace(self, id=None, name=None, is_private=None, is_im=None):
        if id is not None:
            self.id = id
        if name is not None:
            self.name = name
        if is_private is not None:
            self.is_private = is_private
        if is_im is not None:
            self.is_im = is_im
        return self


class Agent:
    def __init__(self, id=None, name=None, is_bot=False, real_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id
        self.name = name
        self.is_bot = is_bot
        self.real_name = real_name

    def replace(self, id=None, name=None, is_bot=None, real_name=None):
        if id is not None:
            self.id = id
        if name is not None:
            self.name = name
        if is_bot is not None:
            self.is_bot = is_bot
        if real_name is not None:
            self.real_name = real_name
        return self


class Notice:
    def __init__(self, channel=None, id=None, text=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel = channel
        self.id = id
        self.text = text

    def replace(self, channel=None, id=None, text=None):
        if channel is not None:
            self.channel = channel
        if id is not None:
            self.id = id
        if text is not None:
            self.text = text
        return self


class BaseService:
    def broadcast(self, channel=None, text=None):
        """Broadcast a message to a channel

        This may return a value (which might be utilised by other Service methods)"""
        raise NotImplementedError()

    def new_channel(self, name=None, private=False, invite=None):
        """Create a new channel and invite users into it

        This returns a serialisable handle to the channel."""
        raise NotImplementedError()

    def delete_channel(self, channel=None):
        """Remove a channel completely"""
        raise NotImplementedError()

    def invite_to_channel(self, channel=None, invite=None):
        """Pull one or more users into a channel

        The bot user associated with this service may need to be in the invite list.
        Passing `None` is harmless."""
        raise NotImplementedError()

    def lookup_channel(self, channel=None):
        """Given a channel, fill in any missing details from its description"""
        raise NotImplementedError()

    def lookup_user(self, agent=None):
        """Given an Agent, fill in any missing details from its description"""
        raise NotImplementedError()

    def post_notice(self, channel=None, notice=None, text=None):
        """Post or update a notice in a channel

        Implementations may vary in how they deal with this. Note, this may be called quite frequently,
        so it should not simply spam a channel with non-updates.

        It should return a Notice, which will identify the notice/pinned message, as applicable."""
        raise NotImplementedError()

    def delete_message(self, channel=None, message_id=None):
        """Remove a message from a channel

        Assuming that's possible."""
        raise NotImplementedError()

    def whisper(self, channel=None, agent=None, text=None):
        """Deliver a message to a single user, within a channel"""
        raise NotImplementedError()
