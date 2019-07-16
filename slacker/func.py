import base64
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
        TEAM = load_secret(cfg, 'TEAM')
    if SERVICE is None:
        SERVICE = SlackService(team=TEAM,
                               bot_oauth=load_secret(cfg, 'BOT_OAUTH'),
                               user_oauth=load_secret(cfg, 'USER_OAUTH'))
    if TOKEN is None:
        TOKEN = load_secret(cfg, 'TOKEN')
    if NAMESPACE is None:
        NAMESPACE = cfg['NAMESPACE']
    if BUCKET is None:
        BUCKET = cfg['BUCKET']


def load_secret(cfg, setting):
    """If we have KMS_KEY and KMS_EP defined, use those to decrypt the given secret

    Otherwise, pull the value out as plaintext."""
    value = cfg.get(setting)
    if value is None:
        return value

    # Retrieve key OCID and endpoint
    key = cfg.get("KMS_KEY")
    endpoint = cfg.get("KMS_EP")

    if key is None and endpoint is None:
        return value

    # Create decryption client
    signer = oci.auth.signers.get_resource_principals_signer()
    client = oci.key_management.KmsCryptoClient({}, endpoint, signer=signer)

    # The plaintext is returned as base64-encoded data. Decrypt it (providing a byte sequence)
    # and then produce a UTF-8 string from the result.
    return base64.b64decode(client.decrypt(oci.key_management.models.DecryptDataDetails(
        key_id=key, ciphertext=value)).data.plaintext).decode("utf-8")


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

                rp = oci.auth.signers.get_resource_principals_signer()
                dispatcher = Dispatcher(srv=SERVICE,
                                        default=bot_class, factory=bot_class.load,
                                        signer=rp, namespace=NAMESPACE, bucket=BUCKET)
                dispatcher.dispatch(sender=sender, channel=channel, receivers=receivers, text=text)

    except Exception as e:
        LOG.exception("Problem during dispatch: %r", e)
        return response.Response(ctx, status_code=500)

    return response.Response(ctx, status_code=200)
