from math import gcd
from functools import reduce

def _weighted_sequence(weights: list[int]) -> list[int]:
    g = reduce(gcd, weights) or 1
    seq = []
    for idx, w in enumerate(weights):
        seq += [idx] * (w // g)
    return seq or [0]

def pick_variant_index(automation, order: int, variants: list[dict]) -> int:
    '''Incrementa o contador da Automation e devolve o indice'''
    from django.db import transaction
    from .models import Automation

    weights = [max(1, int(v.get('weight', 1))) for v in variants]
    seq = _weighted_sequence(weights)
    with transaction.atomic():
        auto = Automation.objects.select_for_update().get(id=automation.id)
        state = dict(auto.variant_state or {})
        counter = int(state.get(str(order), 0))
        state[str(order)] = counter + 1
        auto.variant_state = state
        auto.save(update_fields=['variant_state'])
    return seq[counter % len(seq)]
