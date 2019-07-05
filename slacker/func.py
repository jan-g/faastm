import io
from fdk import response
import json
import logging
import oci

from .base import BaseDispatch
from .dispatch import Dispatcher
from .service import SlackService, Agent, Channel
from .text import Text


LOG = logging.getLogger(__name__)

SERVICE = None
TOKEN = None
TEAM = None
NAMESPACE, BUCKET = None, None


def init(cfg):
    global SERVICE, TOKEN, TEAM, NAMESPACE, BUCKET
    if TEAM is None:
        TEAM = cfg['TEAM']
    if SERVICE is None:
        SERVICE = SlackService(team=TEAM, bot_oauth=cfg['BOT_OAUTH'])
    if TOKEN is None:
        TOKEN = cfg['TOKEN']
    if NAMESPACE is None:
        NAMESPACE = cfg['NAMESPACE']
    if BUCKET is None:
        BUCKET = cfg['BUCKET']


class Bot(BaseDispatch):
    pass


def handle(ctx, data: io.BytesIO, bot_class=Bot):
    init(ctx.Config())
    try:
        args = json.loads(data.getvalue())
        LOG.debug('args are %s', {k: args[k] for k in args if k != 'token'})

        token = args.get('token')
        if token != TOKEN:
            return response.Response(ctx, status_code=401)

        if args.get('challenge') is not None:
            return response.Response(ctx, status_code=200, response_data=args['challenge'])

        team = args.get('team_id')
        if team != TEAM:
            return response.Response(ctx, status_code=404)

        if SERVICE is None:
            return response.Response(ctx, status_code=404)

        if args.get('type') == 'event_callback':
            event = args.get('event', {})

            if event.get('type') == 'app_mention':
                pass
            elif event.get('type') == 'message' and event.get('subtype') is None:

                text = Text.parse(event.get('text', ''), srv=SERVICE)
                text.ts = event.get('ts')
                sender = Agent(id=event.get('user'))
                channel = Channel(id=event.get('channel'))
                if event.get('channel_type') == 'group':
                    channel = channel.replace(is_private=True)
                elif event.get('channel_type') == 'im':
                    channel = channel.replace(is_im=True)
                receivers = [Agent(id=rcv, is_bot=True) for rcv in args.get('authed_users', [])]

                rp = oci.auth.signers.EphemeralResourcePrincipalSigner()
                dispatcher = Dispatcher(srv=SERVICE,
                                        default=bot_class, factory=bot_class.load,
                                        signer=rp, namespace=NAMESPACE, bucket=BUCKET)
                dispatcher.dispatch(sender=sender, channel=channel, receivers=receivers, text=text)

    except Exception as e:
        LOG.exception("Problem during dispatch: %r", e)
        return response.Response(ctx, status_code=500)

    return response.Response(ctx, status_code=200)
