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

        mapped = {s['pipedrive_field']: collected.get(s['key'])
                  for s in (agent.goal_slots or [])
                  if s.get('pipedrive_field') and collected.get(s['key']) is not None}
        if mapped and conversation.pipedrive_deal_id:
            from integrations.models import PipedriveIntegration
            from integrations.pipedrive_services import update_deal_fields
            integ = PipedriveIntegration.objects.filter(
                organization_id=agent.organization_id, is_active=True
            ).first()
            if integ:
                update_deal_fields(integ.api_key, conversation.pipedrive_deal_id, mapped)

        from automations.models import Automation, AutomationRun
        from automations.events import trigger_event
        from automations.tasks import run_automation
        ctx = {'conversation_id': conversation.id, 'contact_id': contact.id, 'agent_id': agent.id, 'collected': collected}
        if action == 'trigger_automation' and agent.goal_automation_id:
            auto = Automation.objects.filter(id=agent.goal_automation_id, is_active=True).first()
            if auto:
                run = AutomationRun.objects.create(automation=auto, context=ctx)
                run_automation.delay(run.id)
        else:    
            trigger_event(
                'agent.goal_completed',
                organization_id=agent.organization_id,
                **ctx
            )
    except Exception:
        logger.exception('[handle_goal_completion] falha aplicando ação')