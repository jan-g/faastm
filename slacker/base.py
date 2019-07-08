import functools
import logging
import time


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


def debounce(timeout, **kwargs):
    """Use:
    @debounce(text=lambda t: t.id, ...)
    def on_message(self, foo=..., bar=..., text=None, ...)"""
    keys = sorted(kwargs.items())

    def wrapper(f):
        @functools.wraps(f)
        def handler(self, *args, **kwargs):
            # Construct a tuple of keys from the input args
            key = tuple(fn(kwargs.get(k)) for k, fn in keys)

            curr = set()
            if hasattr(self, '__debounce_curr'):
                curr = self.__debounce_curr
            prev = set()
            if hasattr(self, '__debounce_prev'):
                prev = self.__debounce_prev
            now = time.time()
            tick = time.time()
            if hasattr(self, '__debounce_tick'):
                tick = self.__debounce_tick

            # Check the current and previous sets, if present
            if key in curr or key in prev:
                return

            # Rotate and update
            if now > tick:
                prev = curr
                curr = set()
                tick = now + timeout

            curr.add(key)

            self.__debounce_curr = curr
            self.__debounce_prev = prev
            self.__debounce_tick = tick

            # Call the wrapped function
            return f(self, *args, **kwargs)

        return handler
    return wrapper
