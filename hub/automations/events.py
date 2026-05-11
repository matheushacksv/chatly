from .models import Automation, AutomationRun


def _matches_filters(filters: dict, context: dict) -> bool:
    if not filters:
        return True
    for key, expected in filters.items():
        if context.get(key) != expected:
            return False
    return True


def trigger_event(event_type: str, organization_id: int, **context):
    '''Chama no insertion point. Enfileira run_automation pra cada Automation ativa.'''
    if context.get('from_automation'):
        return

    from automations.tasks import run_automation

    automations = Automation.objects.filter(
        organization_id=organization_id,
        trigger_type=event_type,
        is_active=True,
    )

    for auto in automations:
        if not _matches_filters(auto.trigger_filters, context):
            continue
        run = AutomationRun.objects.create(automation=auto, context=context)
        run_automation.delay(run.id)
