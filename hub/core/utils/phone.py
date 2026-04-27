import re


def normalize_phone(phone: str) -> str:
    """
    Normaliza número de telefone para o formato internacional sem símbolos.

    Regra brasileira: números com código 55 + DDD (2 dígitos) + 8 dígitos
    (total 12) recebem o 9 inserido após o DDD, ficando com 13 dígitos.

    Exemplos:
        554896436646  → 5548996436646  (adiciona 9 após DDD)
        5548996436646 → 5548996436646  (já normalizado)
        5511999999999 → 5511999999999  (já normalizado)
    """
    phone = re.sub(r'\D', '', phone)

    if phone.startswith('55') and len(phone) == 12:
        phone = phone[:4] + '9' + phone[4:]

    return phone
