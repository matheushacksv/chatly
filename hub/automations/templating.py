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

    def _contact_dict(c):
        return {
            'id': c.id,
            'name': c.name or '',
            'phone': c.phone or '',
            'email': c.email or '',
            'custom_fields': c.custom_fields or {}
        }
    
    contact_id = run_context.get('contact_id')
    if contact_id:
        contact = Contact.objects.filter(id=contact_id).first()
        if contact:
            ctx['contact'] = _contact_dict(contact)

    conversation_id = run_context.get('conversation_id')
    if conversation_id:
        conv = Conversation.objects.filter(id=conversation_id).select_related('contact').first()
        if conv:
            ctx['conversation'] = {
                'id': conv.id,
                'status': conv.status,
                'ai_active': conv.ai_active,
                'assigned_to_id': conv.assigned_to_id,
                'assigned_to': (
                    getattr(conv.assigned_to, 'email', '')
                    if conv.assigned_to_id else ''
                ),
                'instance_id': conv.instance_id,
                'instance': getattr(conv.instance, 'instance_name', '') if conv.instance_id else '',
            }
            if 'contact' not in ctx and conv.contact:
                ctx['contact'] = _contact_dict(conv.contact)

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
