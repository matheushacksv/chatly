import re

_VAR_RE = re.compile(r'\{\{\s*([\w.]+)\s*\}\}')


def render_template(template: str, ctx: dict) -> str:
    if not template:
        return ''

    def repl(m):
        path = m.group(1).split('.')
        val = ctx
        for p in path:
            if val is None:
                return ''
            if isinstance(val, dict):
                val = val.get(p)
            else:
                val = getattr(val, p, None)
        return '' if val is None else str(val)

    return _VAR_RE.sub(repl, template)


def build_context(run_context: dict) -> dict:
    '''Carrega objetos do contexto persistido em dicionários renderizáveis.'''
    from contacts.models import Contact
    from conversations.models import Conversation, Message

    ctx = {}

    contact_id = run_context.get('contact_id')
    if contact_id:
        contact = Contact.objects.filter(id=contact_id).first()
        if contact:
            ctx['contact'] = {
                'id': contact.id,
                'name': contact.name or '',
                'phone': contact.phone or '',
                'email': contact.email or '',
            }

    conversation_id = run_context.get('conversation_id')
    if conversation_id:
        conv = Conversation.objects.filter(id=conversation_id).select_related('contact').first()
        if conv:
            ctx['conversation'] = {
                'id': conv.id,
                'status': conv.status,
            }
            if 'contact' not in ctx and conv.contact:
                ctx['contact'] = {
                    'id': conv.contact.id,
                    'name': conv.contact.name or '',
                    'phone': conv.contact.phone or '',
                    'email': conv.contact.email or '',
                }

    message_id = run_context.get('message_id')
    if message_id:
        msg = Message.objects.filter(id=message_id).first()
        if msg:
            ctx['message'] = {
                'id': msg.id,
                'content': msg.content or '',
                'role': msg.role,
            }

    return ctx
