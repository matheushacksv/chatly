from .models import GoalCompletion
import logging

logger = logging.getLogger(__name__)

def handle_goal_completion(agent, conversation, contact, reason, collected):
    try:
        GoalCompletion.objects.create(
            agent=agent, conversation=conversation, contact=contact,
            collected_data=collected, reason=reason
        )

        if collected:
            cf = contact.custom_fields or {}
            cf.update(collected)
            contact.custom_fields = cf
            contact.save(update_fields=['custom_fields'])

        if agent.goal_final_message:
            from conversations.tasks import send_whatsapp_message
            from conversations.models import Message
            msg = Message.objects.create(
                conversation=conversation, role='assistant',
                content=agent.goal_final_message,
            )
            send_whatsapp_message.delay(msg.id, conversation.instance_id)

        updates = {}
        action = agent.goal_action
        if action == 'deactivate_ai':
            updates['ai_active'] = False
        elif action == 'close_conversation':
            updates['status'] = 'closed'
            updates['ai_active'] = False
        elif action == 'assign_to_user':
            updates['assigned_to_id'] = agent.goal_assign_to_id
            updates['ai_active'] = False
        if updates:
            for k, v in updates.items():
                setattr(conversation, k, v)
            conversation.save(update_fields=list(updates.keys()))

        from automations.events import trigger_event
        trigger_event(
            'agent.goal_completed',
            organization_id=agent.organization_id,
            conversation_id=conversation.id,
            contact_id=contact.id,
            agent_id=agent.id,
            collected=collected
        )
    except Exception:
        logger.exception('[handle_goal_completion] falha aplicando ação')