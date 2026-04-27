from integrations.models import PipedriveIntegration
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from typing import Optional
from ninja import Router
from django.conf import settings
from agents.models import AIAgent
from core.utils.errors import ErrorWithCodeSchema
from .models import WhatsAppInstance, AssignmentQueue, AssignmentQueueMember
from .schemas import WhatsAppInstanceIn, WhatsAppInstanceOut, ConnectIn, QRCodeOut, PairCodeOut, PairCodeIn, MoveStageIn, QueueIn, QueueOut
from . import services as evogo_services
from accounts.utils import is_owner_or_admin

router = Router(tags=['WhatsApp'])

@router.get('/', response=list[WhatsAppInstanceOut])
def list_instances(request):
    return WhatsAppInstance.objects.filter(organization=request.auth.organization)

@router.post('/', response={201: WhatsAppInstanceOut, 400: ErrorWithCodeSchema})
def create_instance(request, data: WhatsAppInstanceIn):

    from billing.services import check_instance_limit

    if not check_instance_limit(request.auth.organization):
        return 400, ErrorWithCodeSchema(detail='Limite de instâncias atingido no plano atual', code='instance_limit_reached')

    if WhatsAppInstance.objects.filter(instance_name=data.name).exists():
        return 400, ErrorWithCodeSchema(detail='Instance in use', code='instance_in_use')

    agent = None
    if data.agent_id:
        try:
            agent = AIAgent.objects.get(id=data.agent_id, organization=request.auth.organization)
        except AIAgent.DoesNotExist:
            return 400, ErrorWithCodeSchema(detail='Agente not found', code='agent_not_found')

    try:
        result = evogo_services.create_instance(data.name)
    except Exception as e:
        return 400, ErrorWithCodeSchema(detail=f'Error in creating Whatsapp instance: {str(e)}', code='error_whatsapp')

    instance = WhatsAppInstance.objects.create(
        organization=request.auth.organization,
        agent=agent,
        instance_name=data.name,
        instance_api_key=result['data']['token']
    )
    return 201, instance

@router.post('/{instance_id}/connect', response={200:dict, 404: ErrorWithCodeSchema, 400: ErrorWithCodeSchema})
def connect_instance(request, instance_id: int, data: ConnectIn):

    try:
        instance = WhatsAppInstance.objects.get(id=instance_id, organization=request.auth.organization)
    except WhatsAppInstance.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Instance not found', code='instance_not_found')

    webhook_url = f'{settings.BASE_URL}/api/webhooks/whatsapp/{instance.instance_name}/'

    try:
        result = evogo_services.connect_instance(instance.instance_api_key, webhook_url)
        instance.status = WhatsAppInstance.Status.CONNECTING
        instance.save()
        return 200, result
    except Exception as e:
        return 400, ErrorWithCodeSchema(detail=f'Connection error: {str(e)}', code='connection_error')

@router.delete('/{instance_id}/logout', response={200: WhatsAppInstanceOut, 400: ErrorWithCodeSchema})
def logout_instance(request, instance_id: int):

    try:
        instance = WhatsAppInstance.objects.get(id=instance_id, organization=request.auth.organization)
    except WhatsAppInstance.DoesNotExist:
        return 400, ErrorWithCodeSchema(detail='Instance not found', code='instance_not_found')

    try:
        result = evogo_services.logout_instance(instance.instance_api_key)
        instance.status = WhatsAppInstance.Status.DISCONNECTED
        instance.save()
        return 200, instance
    except Exception as e:
        return 400, ErrorWithCodeSchema(detail=f'Logout error: {str(e)}', code='logout_error')


@router.get('/{instance_id}/qr', response={200: QRCodeOut, 400: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def get_qr(request, instance_id: int):

    try:
        instance = WhatsAppInstance.objects.get(id=instance_id, organization=request.auth.organization)
    except WhatsAppInstance.DoesNotExist:
        return 400, ErrorWithCodeSchema(detail='Instance not found', code='instance_not_found')

    try:
        result = evogo_services.get_qr(instance.instance_api_key)
        return 200, result['data']
    except Exception as e:
        return 400, ErrorWithCodeSchema(detail=f'QR code error: {str(e)}', code='qrcode_error')

@router.post('/{instance_id}/pair', response={200: PairCodeOut, 400: ErrorWithCodeSchema})
def get_pair_code(request, instance_id: int, data: PairCodeIn):

    try:
        instance = WhatsAppInstance.objects.get(id=instance_id, organization=request.auth.organization)
    except WhatsAppInstance.DoesNotExist:
        return 400, ErrorWithCodeSchema(detail='Instance not found', code='instance_not_found')

    try:
        result = evogo_services.get_pair_code(instance_api_key=instance.instance_api_key, phone=data.phone)
        return 200, {'paircode': result['data']['PairingCode']}
    except Exception as e:
        return 400, ErrorWithCodeSchema(detail=f'Pair code error: {str(e)}', code='pair_code_error')


@router.get('/{instance_id}/status', response={200: WhatsAppInstanceOut, 404: ErrorWithCodeSchema})
def get_status(request, instance_id: int):

    try:
        instance = WhatsAppInstance.objects.get(id=instance_id, organization=request.auth.organization)
    except WhatsAppInstance.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Instance not found', code='instance_not_found')

    try:
        result = evogo_services.get_status(instance.instance_api_key)
        data = result.get('data', {})
        connected = data.get('Connected', False)
        instance.status = WhatsAppInstance.Status.CONNECTED if connected else WhatsAppInstance.Status.DISCONNECTED
        instance.save()
    except Exception as e:
        pass

    return 200, instance

@router.delete('/{instance_id}', response={204: None, 404: ErrorWithCodeSchema, 400: ErrorWithCodeSchema})
def delete_instance(request, instance_id: int):
    
    try:
        instance = WhatsAppInstance.objects.get(id=instance_id, organization=request.auth.organization)
    except WhatsAppInstance.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Instance not found', code='instance_not_found')

    try:
        evogo_services.delete_instance(instance.instance_name, instance.instance_api_key)
    except Exception as e:
        return 400, ErrorWithCodeSchema(detail=f'Error in deleting instance: {str(e)}', code='instance_delete_error')

    instance.delete()
    return 204, None

@router.patch('/{instance_id}/agent', response={200: WhatsAppInstanceOut, 400: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def assign_agent(request, instance_id: int, agent_id: Optional[int] = None):
    try:
        instance = WhatsAppInstance.objects.get(id=instance_id, organization=request.auth.organization)
    except WhatsAppInstance.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Instance not found', code='instance_not_found')

    if agent_id:
        try:
            agent = AIAgent.objects.get(id=agent_id, organization=request.auth.organization)
        except AIAgent.DoesNotExist:
            return 400, ErrorWithCodeSchema(detail='Agent not found', code='agent_not_found')
        instance.agent = agent
    else:
        instance.agent = None

    instance.save()
    return 200, instance
        
#* ------ Queue Endpoints ------

def _queue_response(queue):
    return {
        'id': queue.id,
        'is_active': queue.is_active,
        'members': [
            {
                'user_id': m.user_id,
                'user_name': m.user.name or m.user.email,
                'percentage': m.percentage,
                'assignment_count': m.assignment_count,
            }
            for m in queue.members.select_related('user').order_by('id')
        ]
    }

@router.get('/{instance_id}/queue', response={200: QueueOut, 404: ErrorWithCodeSchema})
def get_queue(request, instance_id: int):
    instance = get_object_or_404(WhatsAppInstance, id=instance_id, organization=request.auth.organization)
    ct = ContentType.objects.get_for_model(WhatsAppInstance)
    try:
        queue = AssignmentQueue.objects.get(content_type=ct, object_id=instance.id)
    except AssignmentQueue.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Fila não configurada', code='queue_not_found')
    return 200, _queue_response(queue)

@router.put('/{instance_id}/queue', response={200: QueueOut, 422: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def upsert_queue(request, instance_id: int, data: QueueIn):
    if not is_owner_or_admin(request.auth):
        return 403, ErrorWithCodeSchema(detail='Permissão negada', code='forbidden')
    instance = get_object_or_404(WhatsAppInstance, id=instance_id, organization=request.auth.organization)
    if not data.members:
        return 422, ErrorWithCodeSchema(detail='A fila deve ter pelo menos um membro', code='empty_queue')
    if sum(m.percentage for m in data.members) != 100:
        return 422, ErrorWithCodeSchema(detail='Percentuais devem somar 100%', code='invalid_percentage')
    ct = ContentType.objects.get_for_model(WhatsAppInstance)
    queue, _ = AssignmentQueue.objects.get_or_create(
        content_type=ct, object_id=instance.id,
        defaults={'organization': request.auth.organization, 'is_active': data.is_active}
    )
    queue.is_active = data.is_active
    queue.save(update_fields=['is_active'])
    existing = {m.user_id: m for m in queue.members.all()}
    new_ids = {m.user_id for m in data.members}
    for uid, member in existing.items():
        if uid not in new_ids:
            member.delete()
    for m_data in data.members:
        if m_data.user_id in existing:
            existing[m_data.user_id].percentage = m_data.percentage
            existing[m_data.user_id].save(update_fields=['percentage'])
        else:
            AssignmentQueueMember.objects.create(queue=queue, user_id=m_data.user_id, percentage=m_data.percentage)
    return 200, _queue_response(queue)

@router.delete('/{instance_id}/queue', response={204: None, 404: ErrorWithCodeSchema})
def delete_queue(request, instance_id: int):
    if not is_owner_or_admin(request.auth):
        return 403, ErrorWithCodeSchema(detail='Permissão negada', code='forbidden')
    instance = get_object_or_404(WhatsAppInstance, id=instance_id, organization=request.auth.organization)
    ct = ContentType.objects.get_for_model(WhatsAppInstance)
    try:
        AssignmentQueue.objects.get(content_type=ct, object_id=instance.id).delete()
    except AssignmentQueue.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Fila não encontrada', code='queue_not_found')
    return 204, None
