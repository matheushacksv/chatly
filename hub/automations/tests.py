from unittest.mock import patch

from django.test import TestCase

from accounts.models import Organization
from contacts.models import Contact

from .conditions import evaluate_condition
from .models import Automation, AutomationStep, AutomationRun
from .tasks import run_automation


# ---------------------------------------------------------------------------
# Tipo 1 — evaluate_condition (função pura)
# ---------------------------------------------------------------------------
class EvaluateConditionTests(TestCase):
    def _ctx(self):
        return {
            'contact': {'name': 'Maria', 'email': 'maria@x.com',
                        'custom_fields': {'plano': 'VIP', 'idade': '30'}},
            'conversation': {'status': 'open'},
        }

    def test_sem_regras_passa(self):
        self.assertTrue(evaluate_condition({}, self._ctx()))
        self.assertTrue(evaluate_condition({'combinator': 'AND', 'rules': []}, self._ctx()))

    def test_equals_string(self):
        logic = {'rules': [{'field': 'contact.custom_fields.plano', 'op': 'equals', 'value': 'VIP'}]}
        self.assertTrue(evaluate_condition(logic, self._ctx()))
        logic['rules'][0]['value'] = 'free'
        self.assertFalse(evaluate_condition(logic, self._ctx()))

    def test_equals_case_insensitive(self):
        logic = {'rules': [{'field': 'contact.custom_fields.plano', 'op': 'equals', 'value': 'vip'}]}
        self.assertTrue(evaluate_condition(logic, self._ctx()))

    def test_equals_numerico(self):
        logic = {'rules': [{'field': 'contact.custom_fields.idade', 'op': 'equals', 'value': 30}]}
        self.assertTrue(evaluate_condition(logic, self._ctx()))

    def test_not_equals(self):
        logic = {'rules': [{'field': 'conversation.status', 'op': 'not_equals', 'value': 'closed'}]}
        self.assertTrue(evaluate_condition(logic, self._ctx()))

    def test_contains_e_not_contains(self):
        ctx = self._ctx()
        self.assertTrue(evaluate_condition(
            {'rules': [{'field': 'contact.name', 'op': 'contains', 'value': 'ari'}]}, ctx))
        self.assertTrue(evaluate_condition(
            {'rules': [{'field': 'contact.name', 'op': 'not_contains', 'value': 'zzz'}]}, ctx))

    def test_is_empty(self):
        ctx = {'contact': {'name': '', 'custom_fields': {}}}
        self.assertTrue(evaluate_condition(
            {'rules': [{'field': 'contact.name', 'op': 'is_empty', 'value': ''}]}, ctx))
        self.assertTrue(evaluate_condition(
            {'rules': [{'field': 'contact.custom_fields.x', 'op': 'is_empty', 'value': ''}]}, ctx))

    def test_combinator_and(self):
        logic = {'combinator': 'AND', 'rules': [
            {'field': 'contact.custom_fields.plano', 'op': 'equals', 'value': 'VIP'},
            {'field': 'conversation.status', 'op': 'equals', 'value': 'open'},
        ]}
        self.assertTrue(evaluate_condition(logic, self._ctx()))
        logic['rules'][1]['value'] = 'closed'
        self.assertFalse(evaluate_condition(logic, self._ctx()))

    def test_combinator_or(self):
        logic = {'combinator': 'OR', 'rules': [
            {'field': 'contact.custom_fields.plano', 'op': 'equals', 'value': 'free'},
            {'field': 'conversation.status', 'op': 'equals', 'value': 'open'},
        ]}
        self.assertTrue(evaluate_condition(logic, self._ctx()))
        logic['rules'][1]['value'] = 'closed'
        self.assertFalse(evaluate_condition(logic, self._ctx()))


# ---------------------------------------------------------------------------
# Tipo 2 — run_automation com ramificação IF/ELSE
# ---------------------------------------------------------------------------
class RunAutomationBranchTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Org', slug='org')

    def _build_automation(self):
        '''Árvore: condição (plano==VIP) -> then[1] / else[2] -> pós-condição[3].'''
        automation = Automation.objects.create(
            organization=self.org, name='Teste', trigger_type='contact.created',
            is_active=True,
        )
        cond = AutomationStep.objects.create(
            automation=automation, order=0, action_type='condition',
            config={'logic': {'combinator': 'AND', 'rules': [
                {'field': 'contact.custom_fields.plano', 'op': 'equals', 'value': 'VIP'},
            ]}},
        )
        AutomationStep.objects.create(
            automation=automation, parent=cond, branch='then', order=1,
            action_type='send_message', config={},
        )
        AutomationStep.objects.create(
            automation=automation, parent=cond, branch='else', order=2,
            action_type='send_message', config={},
        )
        AutomationStep.objects.create(
            automation=automation, order=3, action_type='send_message', config={},
        )
        return automation, cond

    def _run(self, automation, custom_fields):
        contact = Contact.objects.create(
            organization=self.org, name='Cliente', phone=f'5511{id(custom_fields) % 1000000:06d}',
            custom_fields=custom_fields,
        )
        run = AutomationRun.objects.create(
            automation=automation, context={'contact_id': contact.id},
        )
        with patch('automations.actions.execute_action') as mock_exec:
            run_automation.apply(args=[run.id])
        executed = [call.args[0].order for call in mock_exec.call_args_list]
        run.refresh_from_db()
        return run, executed

    def test_branch_then(self):
        automation, cond = self._build_automation()
        run, executed = self._run(automation, {'plano': 'VIP'})

        self.assertEqual(executed, [1, 3])  # then + pós-condição
        self.assertEqual(run.status, AutomationRun.Status.COMPLETED)
        self.assertEqual(run.context['branch_choices'], {str(cond.id): 'then'})

    def test_branch_else(self):
        automation, cond = self._build_automation()
        run, executed = self._run(automation, {'plano': 'free'})

        self.assertEqual(executed, [2, 3])  # else + pós-condição
        self.assertEqual(run.status, AutomationRun.Status.COMPLETED)
        self.assertEqual(run.context['branch_choices'], {str(cond.id): 'else'})
