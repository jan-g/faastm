import logging


LOG = logging.getLogger(__name__)


class BaseDispatch:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_message(self, srv=None, sender=None, receivers=None, channel=None, text=None):
        LOG.debug("Just received a message from %s to %s: %r", sender, channel, text)

    def save(self):
        return self

    @classmethod
    def load(cls, value):
        return value
