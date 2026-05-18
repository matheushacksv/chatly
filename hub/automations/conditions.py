def _resolve_field(path: str, ctx: dict):
    '''Resolve caminho pontilhado (ex: contact.custom_fields.plano) sobre o context'''
    val = ctx
    for part in path.split('.'):
        if val is None:
            return None
        if isinstance(val, dict):
            val = val.get(part)
        else:
            val = getattr(val, part, None)
    return val

def _as_number(v):
    '''Tenta converter para float. None se não for number'''
    try:
        return float(str(v).replace(',', '.'))
    except (ValueError, TypeError):
        return None
    
def _eval_rule(rule: dict, ctx: dict) -> bool:
    field = rule.get('field', '')
    op = rule.get('op', '')
    expected = rule.get('value', '')

    actual = _resolve_field(field, ctx)

    if op == 'is_empty':
        return actual in (None, '', [], {})
    if op == 'is_not_empty':
        return actual not in (None, '', [], {})
    
    a_str = '' if actual is None else str(actual)
    e_str = '' if expected is None else str(expected)

    if op in ('equals', 'not_equals'):
        a_num, e_num = _as_number(actual), _as_number(expected)
        if a_num is not None and e_num is not None:
            equal = a_num == e_num
        else:
            equal = a_str.strip().casefold() == e_str.strip().casefold()
        return equal if op == 'equals' else not equal
    
    if op in ('contains', 'not_contains'):
        has = e_str.strip().casefold() in a_str.casefold()
        return has if op == 'contains' else not has

    return False

def evaluate_condition(logic: dict, ctx: dict) -> bool:
    '''logic = {'combinator': 'AND'|'OR', 'rules': [{field, op, value}, ...]}'''
    rules = logic.get('rules') or []
    if not rules:
        return True
    
    results = [_eval_rule(r, ctx) for r in rules]
    combinator = (logic.get('combinator') or 'AND').upper()
    return all(results) if combinator == 'AND' else any(results)