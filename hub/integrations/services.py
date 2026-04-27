import uuid
import httpx
from django.conf import settings

def _global_headers():
    return {'apikey': settings.EVOGO_GLOBAL_API_KEY}

def _instance_headers(api_key: str):
    return {'apikey': api_key}

def create_instance(name: str) -> dict:
    token = str(uuid.uuid4())
    response = httpx.post(
        f'{settings.EVOGO_BASE_URL}/instance/create',
        headers=_global_headers(),
        json={'name': name, 'token': token},
        timeout=30.0,
        follow_redirects=True
    )
    return response.json()

def connect_instance(instance_api_key: str, webhook_url: str) -> dict:
    response = httpx.post(
        f'{settings.EVOGO_BASE_URL}/instance/connect/',
        headers=_instance_headers(instance_api_key),
        json={
            'immediate': True,
            'subscribe': ['MESSAGE', 'CONNECTION'],
            'webhookUrl': webhook_url
        },
        timeout=30.0,
        follow_redirects=True
    )
    response.raise_for_status()
    return response.json()

def get_qr(instance_api_key: str) -> dict:
    response = httpx.get(
        f'{settings.EVOGO_BASE_URL}/instance/qr',
        headers=_instance_headers(instance_api_key),
        follow_redirects=True,
        timeout=30.0
    )
    response.raise_for_status()
    return response.json()


def get_pair_code(instance_api_key: str, phone: str) -> dict:
    response = httpx.post(
        f'{settings.EVOGO_BASE_URL}/instance/pair',
        headers=_instance_headers(instance_api_key),
        json={'phone': phone},
        timeout=30.0,
        follow_redirects=True
    )
    response.raise_for_status()
    return response.json()


def get_status(instance_api_key: str) -> dict:
    response = httpx.get(
        f'{settings.EVOGO_BASE_URL}/instance/status',
        headers=_instance_headers(instance_api_key),
        follow_redirects=True
    )
    response.raise_for_status()
    return response.json()

def delete_instance(instance_id: str, instance_api_key: str) -> None:
    response = httpx.delete(
        f'{settings.EVOGO_BASE_URL}/instance/delete/{instance_id}',
        headers=_instance_headers(instance_api_key),
        follow_redirects=True,
        timeout=30.0,
    )
    response.raise_for_status()

def send_message(instance_api_key: str, phone: str, text: str) -> dict:
    response = httpx.post(
        f'{settings.EVOGO_BASE_URL}/send/text',
        headers=_instance_headers(instance_api_key),
        json={'number': phone, 'text': text},
        timeout=30.0,
        follow_redirects=True
    )
    response.raise_for_status()
    return response.json()

def send_media(instance_api_key: str, phone: str, media_url: str, media_type: str, mime_type: str, caption: str = '') -> dict:
    response = httpx.post(
        f'{settings.EVOGO_BASE_URL}/send/media',
        headers=_instance_headers(instance_api_key),
        json={
            'number': phone,
            'type': media_type,
            'caption': caption,
            'url': media_url,
        },
        timeout=30.0,
        follow_redirects=True
    )
    response.raise_for_status()
    return response.json()

def send_sticker(instance_api_key: str, phone: str, sticker_url: str) -> dict:
    response = httpx.post(
        f'{settings.EVOGO_BASE_URL}/send/sticker',
        headers=_instance_headers(instance_api_key),
        json={'number': phone, 'sticker': sticker_url},
        timeout=30.0,
        follow_redirects=True
    )
    response.raise_for_status()
    return response.json()

def logout_instance(instance_api_key: str):
    response = httpx.delete(
        f'{settings.EVOGO_BASE_URL}/instance/logout',
        headers=_instance_headers(instance_api_key),
        timeout=30.0,
        follow_redirects=True
    )
    response.raise_for_status()
    return response.json()


#* ----- Algoritmo de distribuição -----

def assign_from_queue(queue, conversation):
    from django.db import models as db_models
    from integrations.models import AssignmentQueueMember
    members = list(queue.members.select_related('user'))
    if not members:
        return
    total = sum(m.assignment_count for m in members)
    best = max(members, key=lambda m: m.percentage / 100 - (m.assignment_count / max(total, 1)))
    conversation.assigned_to = best.user
    conversation.save(update_fields=['assigned_to'])
    AssignmentQueueMember.objects.filter(id=best.id).update(
        assignment_count=db_models.F('assignment_count') + 1
    )

