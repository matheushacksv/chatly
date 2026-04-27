from django.core.files.storage import default_storage
from ninja import UploadedFile
from ninja import Router, File
from .models import AIProvider, AIAgent, AgentMembership, AgentDocument, AgentCustomTool
from .schemas import AIProviderIn, AIProviderOut, AIAgentIn, AIAgentOut, AgentMembershipIn, AgentMembershipOut, AgentDocumentOut, AgentCustomToolIn, AgentCustomToolOut
from core.utils.errors import ErrorWithCodeSchema
from accounts.models import User
from django.shortcuts import get_object_or_404
import uuid
from .tasks import process_agent_document
from accounts.utils import is_owner_or_admin, has_permission


router = Router(tags=['Agents'])


#* ----- Providers -----

@router.get('/providers', response=list[AIProviderOut])
def list_providers(request):
    return AIProvider.objects.filter(organization=request.auth.organization)

@router.post('/providers', response={201: AIProviderOut, 400: ErrorWithCodeSchema, 403: ErrorWithCodeSchema})
def create_provider(request, data: AIProviderIn):
    if not is_owner_or_admin(request.auth):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')

    if AIProvider.objects.filter(organization=request.auth.organization, provider_type=data.provider_type).exists():
        return 400, ErrorWithCodeSchema(detail='Provider already registered', code='provider_already_registered')

    provider = AIProvider.objects.create(organization=request.auth.organization, **data.dict())
    return 201, provider

@router.delete('/providers/{provider_id}', response={204: None, 403: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def delete_provider(request, provider_id: int):
    if not is_owner_or_admin(request.auth):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')

    try:
        provider = AIProvider.objects.get(id=provider_id, organization=request.auth.organization)
    except AIProvider.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Provider do not exist', code='provider_not_exist')

    provider.delete()
    return 204, None

#* ----- Agents -----

@router.get('/', response=list[AIAgentOut])
def list_agents(request):
    return AIAgent.objects.filter(organization=request.auth.organization).select_related('provider')

@router.post('/', response={201: AIAgentOut, 400: ErrorWithCodeSchema, 403: ErrorWithCodeSchema})
def create_agent(request, data: AIAgentIn):
    if not has_permission(request.auth, 'can_create_agents'):
        return 403, ErrorWithCodeSchema(detail='No permission to create agents', code='no_permission')

    try:
        provider = AIProvider.objects.get(id=data.provider_id, organization=request.auth.organization)
    except AIProvider.DoesNotExist:
        return 400, ErrorWithCodeSchema(detail='Provider do not exist', code='provider_not_exist')

    agent = AIAgent.objects.create(
        organization=request.auth.organization,
        provider=provider,
        **{k: v for k, v in data.dict().items() if k != 'provider_id'}
    )
    return 201, agent

@router.get('/{agent_id}', response={200: AIAgentOut, 404: ErrorWithCodeSchema})
def get_agent(request, agent_id: int):
    try:
        return AIAgent.objects.select_related('provider').get(id=agent_id, organization=request.auth.organization)
    except AIAgent.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Agent not found', code='agent_not_found')

@router.put('/{agent_id}', response={200: AIAgentOut, 400: ErrorWithCodeSchema, 403: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def update_agent(request, agent_id: int, data: AIAgentIn):
    if not has_permission(request.auth, 'can_edit_agents'):
        return 403, ErrorWithCodeSchema(detail='No permission to edit agents', code='no_permission')

    try:
        agent = AIAgent.objects.get(id=agent_id, organization=request.auth.organization)
    except AIAgent.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Agent not found', code='agent_not_found')

    try:
        provider = AIProvider.objects.get(id=data.provider_id, organization=request.auth.organization)
    except AIProvider.DoesNotExist:
        return 400, ErrorWithCodeSchema(detail='Provider not found', code='provider_not_found')

    for field, value in data.dict().items():
        if field == 'provider_id':
            agent.provider = provider
        else:
            setattr(agent, field, value)

    agent.save()
    return agent


@router.delete('/{agent_id}', response={204: None, 403: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def delete_agent(request, agent_id: int):
    if not has_permission(request.auth, 'can_delete_agents'):
        return 403, ErrorWithCodeSchema(detail='No permission to delete agents', code='no_permission')

    try:
        agent = AIAgent.objects.get(id=agent_id, organization=request.auth.organization)
    except AIAgent.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Agent not found', code='agent_not_found')

    agent.delete()
    return 204, None


#* ----- Agent Memberships -----

@router.get('/{agent_id}/members', response={200: list[AgentMembershipOut], 404: ErrorWithCodeSchema})
def list_agent_members(request, agent_id: int):
    try:
        agent = AIAgent.objects.get(id=agent_id, organization=request.auth.organization)
    except AIAgent.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Agent not found', code='agent_not_found')

    return 200, agent.memberships.select_related('user').all()


@router.post('/{agent_id}/members', response={201: AgentMembershipOut, 400: ErrorWithCodeSchema, 403: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def add_agent_member(request, agent_id: int, data: AgentMembershipIn):
    if not is_owner_or_admin(request.auth):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')

    try:
        agent = AIAgent.objects.get(id=agent_id, organization=request.auth.organization)
    except AIAgent.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Agent not found', code='agent_not_found')

    try:
        user = User.objects.get(id=data.user_id, organization=request.auth.organization)
    except User.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='User not found', code='user_not_found')

    if AgentMembership.objects.filter(user=user, agent=agent).exists():
        return 400, ErrorWithCodeSchema(detail='User already assigned to this agent', code='already_assigned')

    membership = AgentMembership.objects.create(user=user, agent=agent)
    return 201, membership


@router.delete('/{agent_id}/members/{user_id}', response={204: None, 403: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def remove_agent_member(request, agent_id: int, user_id: int):
    if not is_owner_or_admin(request.auth):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')

    try:
        agent = AIAgent.objects.get(id=agent_id, organization=request.auth.organization)
    except AIAgent.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Agent not found', code='agent_not_found')

    try:
        membership = AgentMembership.objects.get(agent=agent, user_id=user_id)
    except AgentMembership.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Membership not found', code='membership_not_found')

    membership.delete()
    return 204, None


#* ----- Agent Documents (RAG) -----

@router.get('/{agent_id}/documents', response=list[AgentDocumentOut])
def list_documents(request, agent_id: int):
    agent = get_object_or_404(AIAgent, id=agent_id, organization=request.auth.organization)
    return agent.documents.all()

@router.post('/{agent_id}/documents', response={201: AgentDocumentOut})
def upload_document(request, agent_id: int, file: UploadedFile = File(...)):

    agent = get_object_or_404(AIAgent, id=agent_id, organization=request.auth.organization)
    ext = file.name.rsplit('.', 1)[-1].lower()
    path = default_storage.save(f'agent_docs/{uuid.uuid4()}.{ext}', file)
    doc = AgentDocument.objects.create(
        agent=agent,
        name=file.name,
        file_url=default_storage.url(path),
        status='pending'
    )
    process_agent_document.delay(doc.id)
    return 201, doc

@router.delete('/{agent_id}/documents/{doc_id}', response={204: None})
def delete_document(request, agent_id: int, doc_id: int):
    
    doc = get_object_or_404(AgentDocument, id=doc_id, agent_id=agent_id, agent__organization=request.auth.organization)
    doc.delete()
    return 204, None


#* ----- Agent Tools -----

@router.get('/{agent_id}/tools', response=list[AgentCustomToolOut])
def list_agent_tools(request, agent_id: int):
    agent = get_object_or_404(AIAgent, id=agent_id, organization=request.auth.organization)
    return agent.custom_tools.all()

@router.post('/{agent_id}/tools', response={201: AgentCustomToolOut, 400: ErrorWithCodeSchema, 403: ErrorWithCodeSchema})
def create_agent_tool(request, agent_id: int, data: AgentCustomToolIn):

    if not has_permission(request.auth, 'can_edit_agents'):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')

    agent = get_object_or_404(AIAgent, id=agent_id, organization=request.auth.organization)

    if agent.custom_tools.filter(name=data.name).exists():
        return 400, ErrorWithCodeSchema(detail='Tool name already exists for this agent', code='tool_name_exists')

    import json
    tool = AgentCustomTool.objects.create(
        agent=agent,
        name=data.name,
        description=data.description,
        method=data.method,
        url=data.url,
        headers=json.dumps(data.headers),
        body_template=data.body_template
    )
    return 201, tool

@router.put('/{agent_id}/tools/{tool_id}', response={200: AgentCustomToolOut, 400: ErrorWithCodeSchema, 403: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def update_agent_tool(request, agent_id: int, tool_id: int, data: AgentCustomToolIn):

    if not has_permission(request.auth, 'can_edit_agents'):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')

    agent = get_object_or_404(AIAgent, id=agent_id, organization=request.auth.organization)

    try:
        tool = AgentCustomTool.objects.get(id=tool_id, agent=agent)
    except AgentCustomTool.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Tool not found', code='tool_not_found')

    import json
    tool.name = data.name
    tool.description = data.description
    tool.method = data.method
    tool.url = data.url
    tool.headers = json.dumps(data.headers)
    tool.body_template = data.body_template
    tool.save()
    return tool

@router.delete('/{agent_id}/tools/{tool_id}', response={204: None, 403: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def delete_agent_tool(request, agent_id: int, tool_id: int):

    if not has_permission(request.auth, 'can_edit_agents'):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')

    agent = get_object_or_404(AIAgent, id=agent_id, organization=request.auth.organization)

    try:
        tool = AgentCustomTool.objects.get(id=tool_id, agent=agent)
    except AgentCustomTool.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Tool not found', code='tool_not_found')

    tool.delete()
    return 204, None
