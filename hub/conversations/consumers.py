import json
import logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class OrgConsumer(AsyncWebsocketConsumer):
    """
    WebSocket em nível de organização — notifica criação/atualização de conversas.
    Permite que a lista de conversas atualize em tempo real sem polling.
    """

    async def connect(self):
        token = self._get_token()
        if not token:
            await self.close(code=4001)
            return

        user = await self._get_user(token)
        if not user:
            await self.close(code=4001)
            return

        self.org_id = user.organization_id
        self.group_name = f'org_{self.org_id}'

        try:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        except Exception as e:
            # Falha do channel layer (Redis) — logar a causa real em vez de
            # deixar o Daphne fechar com 1011 mudo (cliente entra em loop de reconnect).
            logger.exception(f'[OrgConsumer] group_add falhou (channel layer): {e}')
            await self.close(code=1011)
            return
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def org_event(self, event):
        await self.send(text_data=json.dumps(event['payload']))

    def _get_token(self):
        query_string = self.scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        tokens = params.get('token', [])
        return tokens[0] if tokens else None

    @database_sync_to_async
    def _get_user(self, token_key):
        try:
            from ninja_jwt.tokens import AccessToken
            from accounts.models import User
            access_token = AccessToken(token_key)
            return User.objects.select_related('organization').get(id=access_token['user_id'])
        except Exception as e:
            logger.warning(f'[OrgConsumer] Token inválido: {e}')
            return None


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.group_name = f'conversation_{self.conversation_id}'

        token = self._get_token()
        if not token:
            await self.close(code=4001)
            return

        user = await self._get_user(token)
        if not user:
            await self.close(code=4001)
            return

        has_access = await self._check_access(user, self.conversation_id)
        if not has_access:
            await self.close(code=4003)
            return

        try:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        except Exception as e:
            logger.exception(f'[ChatConsumer] group_add falhou (channel layer): {e}')
            await self.close(code=1011)
            return
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Mensagens são enviadas via HTTP API — este método não é usado
        pass

    # Chamado pelo channel_layer.group_send com type='chat.message'
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['payload']))

    # ------------------------------------------------------------------ #
    # Helpers privados                                                     #
    # ------------------------------------------------------------------ #

    def _get_token(self):
        query_string = self.scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        tokens = params.get('token', [])
        return tokens[0] if tokens else None

    @database_sync_to_async
    def _get_user(self, token_key):
        try:
            from ninja_jwt.tokens import AccessToken
            from accounts.models import User
            access_token = AccessToken(token_key)
            return User.objects.select_related('organization').get(id=access_token['user_id'])
        except Exception as e:
            logger.warning(f'[ChatConsumer] Token inválido: {e}')
            return None

    @database_sync_to_async
    def _check_access(self, user, conversation_id):
        from conversations.models import Conversation
        return Conversation.objects.filter(
            id=conversation_id,
            organization=user.organization,
        ).exists()


# ------------------------------------------------------------------ #
# Funções utilitárias — chame a partir de views, tasks e webhooks    #
# ------------------------------------------------------------------ #

def notify_new_message(conversation_id: int, message) -> None:
    """
    Notifica todos os clientes conectados à conversa sobre uma nova mensagem.
    Pode ser chamado de código síncrono (views, tasks, webhook).
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    payload = {
        'type': 'new_message',
        'message': _serialize_message(message),
    }

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'conversation_{conversation_id}',
            {'type': 'chat.message', 'payload': payload},
        )
    except Exception:
        pass


def notify_attachment_updated(conversation_id: int, attachment) -> None:
    """
    Notifica clientes quando um attachment é atualizado (ex: transcrição concluída).
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    payload = {
        'type': 'attachment_updated',
        'attachment': {
            'id': attachment.id,
            'message_id': attachment.message_id,
            'transcription': attachment.transcription,
            'transcription_status': attachment.transcription_status,
        },
    }

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'conversation_{conversation_id}',
            {'type': 'chat.message', 'payload': payload},
        )
    except Exception:
        pass


def notify_conversation_updated(conversation) -> None:
    """
    Notifica clientes sobre mudanças na conversa (status, ai_active, etc).
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    agent_name = None
    try:
        if conversation.agent_id and conversation.agent:
            agent_name = conversation.agent.name
    except Exception:
        pass

    assigned_to_name = None
    try:
        if conversation.assigned_to_id and conversation.assigned_to:
            assigned_to_name = conversation.assigned_to.name
    except Exception:
        pass

    payload = {
        'type': 'conversation_updated',
        'conversation': {
            'id': conversation.id,
            'status': conversation.status,
            'ai_active': conversation.ai_active,
            'agent_id': conversation.agent_id,
            'agent_name': agent_name,
            'assigned_to_id': conversation.assigned_to_id,
            'assigned_to_name': assigned_to_name,
        },
    }

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'conversation_{conversation.id}',
            {'type': 'chat.message', 'payload': payload},
        )
    except Exception:
        pass


def notify_new_conversation(conversation) -> None:
    """
    Notifica o canal da organização sobre uma nova conversa criada.
    Clientes conectados ao OrgConsumer recebem o evento 'new_conversation'.
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    payload = {
        'type': 'new_conversation',
        'conversation': _serialize_conversation(conversation),
    }

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'org_{conversation.organization_id}',
            {'type': 'org.event', 'payload': payload},
        )
    except Exception:
        pass


def notify_conversation_list_updated(conversation) -> None:
    """
    Notifica o canal da organização sobre mudanças numa conversa (status, last message, etc).
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    payload = {
        'type': 'conversation_list_updated',
        'conversation': _serialize_conversation(conversation),
    }

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'org_{conversation.organization_id}',
            {'type': 'org.event', 'payload': payload},
        )
    except Exception:
        pass


def _serialize_conversation(conversation) -> dict:
    try:
        contact = conversation.contact
        contact_data = {
            'id': contact.id,
            'name': contact.name or '',
            'phone': contact.phone or '',
        }
    except Exception:
        from contacts.models import Contact as ContactModel
        try:
            c = ContactModel.objects.get(id=conversation.contact_id)
            contact_data = {'id': c.id, 'name': c.name or '', 'phone': c.phone or ''}
        except Exception:
            contact_data = {'id': conversation.contact_id, 'name': '', 'phone': ''}

    agent_name = None
    try:
        if conversation.agent_id and conversation.agent:
            agent_name = conversation.agent.name
    except Exception:
        pass

    assigned_to_name = None
    try:
        if conversation.assigned_to_id and conversation.assigned_to:
            assigned_to_name = conversation.assigned_to.name
    except Exception:
        pass

    last_message = None
    try:
        msg = conversation.messages.order_by('-created_at').first()
        if msg:
            last_message = {
                'id': msg.id,
                'role': msg.role,
                'content': msg.content or '',
                'created_at': msg.created_at.isoformat()
            }
    except Exception:
        pass

    return {
        'id': conversation.id,
        'status': conversation.status,
        'ai_active': conversation.ai_active,
        'started_at': conversation.started_at.isoformat(),
        'agent_id': conversation.agent_id,
        'agent_name': agent_name,
        'assigned_to_id': conversation.assigned_to_id,
        'assigned_to_name': assigned_to_name,
        'contact': contact_data,
        'last_message': last_message
    }


def _serialize_message(message) -> dict:
    sent_by_name = None
    try:
        if message.sent_by_id and message.sent_by:
            sent_by_name = message.sent_by.name
    except Exception:
        pass

    return {
        'id': message.id,
        'role': message.role,
        'content': message.content,
        'sent_by_name': sent_by_name,
        'created_at': message.created_at.isoformat(),
        'attachments': [
            {
                'id': att.id,
                'media_type': att.media_type,
                'file_url': att.file_url,
                'mime_type': att.mime_type,
                'transcription': att.transcription,
                'transcription_status': att.transcription_status,
            }
            for att in message.attachments.all()
        ],
    }
