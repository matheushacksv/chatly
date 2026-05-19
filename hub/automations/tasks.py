import logging
from celery import shared_task
from django.utils import timezone
from .conditions import evaluate_condition
from .templating import build_context
from .utils.helpers import _step_active

from .models import AutomationRun

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, soft_time_limit=60, time_limit=90)
def run_automation(self, run_id: int):
    from .actions import execute_action

    try:
        run = AutomationRun.objects.select_related('automation').get(id=run_id)
    except AutomationRun.DoesNotExist:
        logger.warning('[run_automation] run %s não encontrado', run_id)
        return

    if run.status != AutomationRun.Status.RUNNING:
        return

    steps = list(run.automation.steps.order_by('order'))
    by_id = {s.id: s for s in steps}
    organization_id = run.automation.organization_id

    for step in steps[run.current_step:]:
        try:
            branch_choices = (run.context or {}).get('branch_choices', {})

            if not _step_active(step, by_id, branch_choices):
                run.current_step += 1
                run.save(update_fields=['current_step'])
                continue

            if step.action_type == 'condition':
                ok = evaluate_condition(
                    step.config.get('logic', {}),
                    build_context(run.context or {})
                )
                ctx = dict(run.context or {})
                choices = dict(ctx.get('branch_choices', {}))
                choices[str(step.id)] = 'then' if ok else 'else'
                ctx['branch_choices'] = choices
                run.context = ctx
                run.current_step += 1
                run.save(update_fields=['context', 'current_step'])
                continue

            if step.action_type == 'wait_delay':
                seconds = int(step.config.get('seconds', 60))
                run.current_step = run.current_step + 1
                run.save(update_fields=['current_step'])
                run_automation.apply_async(args=[run.id], countdown=seconds)
                return

            variants = (step.config or {}).get('variants') or []
            if step.action_type == 'send_message' and variants:
                from .variants import pick_variant_index
                i = pick_variant_index(run.automation, step.order, variants)
                step.config = {**step.config, 'text': variants[i].get('text', '')}

            context = dict(run.context or {})
            context['from_automation'] = True
            execute_action(step, context, organization_id)
            run.current_step += 1
            run.save(update_fields=['current_step'])

        except ValueError as exc:
            logger.error('[run_automation] run %s step %s config inválida (terminal): %s', run.id, step.order, exc)
            run.status = AutomationRun.Status.FAILED
            run.error = str(exc)
            run.finished_at = timezone.now()
            run.save(update_fields=['status', 'error', 'finished_at'])
            return
        except Exception as exc:
            logger.error('[run_automation] run %s step %s falhou: %s', run.id, step.order, exc)
            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))
            run.status = AutomationRun.Status.FAILED
            run.error = str(exc)
            run.finished_at = timezone.now()
            run.save(update_fields=['status', 'error', 'finished_at'])
            return

    run.status = AutomationRun.Status.COMPLETED
    run.finished_at = timezone.now()
    run.save(update_fields=['status', 'finished_at'])
