# FaaS-based STM

This is a small library that attempts to do STM to update stored
state in an object-storage system.

It also interacts with the Slack API.

The whole thing works by saving external effects until the
STM commit passes; at that point, the external effects are
committed also.

## Usage

This can be installed in a Fn-style serverless function like this:

    import logging
    
    from slacker import Text, BaseDispatch, handle, debounce
    
    LOG = logging.getLogger(__name__)
    
    
    def handler(ctx, data=None):
        LOG.debug("got request: %s", data)
        try:
            response = handle(ctx, data, bot_class=MyBot)
            LOG.debug("returning %s %s", response.status_code, response.response_data)
            return response
        except Exception as e:
            LOG.exception("something went wrong: %s", e)
    
    
    class MyBot(BaseDispatch):
        @debounce(30, text=lambda t: t.ts)
        def on_message(self, srv=None, sender=None, channel=None, receivers=None, text=None):
            if text.match("hello") is not None:
                srv.broadcast(channel=channel,
                              text=Text("hello, world!"))
