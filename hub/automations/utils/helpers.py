from automations.models import AutomationStep

def _step_active(step, by_id, branch_choices) -> bool:
    '''True se toda a linhagem de branch do passo bate com as escolhas'''
    node = step
    while node.parent_id:
        parent = by_id.get(node.parent_id)
        if parent is None:
            return False
        if branch_choices.get(str(parent.id)) != node.branch:
            return False
        node = parent
    return True

def _validate_steps(steps, valid_actions):
    for s in steps:
        if s.action_type not in valid_actions:
            return s.action_type
        bad = _validate_steps(s.then_steps, valid_actions) or _validate_steps(s.else_steps, valid_actions)
        if bad:
            return bad
    return None

def _save_steps(automation, steps, parent, branch, counter):
    for s in steps:
        node = AutomationStep.objects.create(
            automation=automation,
            parent=parent,
            branch=branch,
            order=counter[0],
            action_type=s.action_type,
            config=s.config,
        )
        counter[0] += 1
        if s.action_type == 'condition':
            _save_steps(automation, s.then_steps, node, 'then', counter)
            _save_steps(automation, s.else_steps, node, 'else', counter)