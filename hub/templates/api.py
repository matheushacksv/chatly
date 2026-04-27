from ninja import Router, File, Form
from ninja.files import UploadedFile
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import uuid
from .models import MessageTemplate
from .schemas import MessageTemplateIn, MessageTemplateOut
from core.utils.errors import GenericErrorSchema, ErrorWithCodeSchema

router = Router(tags=['Templates'])

@router.get('/', response=list[MessageTemplateOut])
def list_templates(request):
    return MessageTemplate.objects.filter(organization=request.auth.organization)


@router.post('/', response={201: MessageTemplateOut, 400: GenericErrorSchema})
def create_text_template(request, data: MessageTemplateIn):
    try:
        template = MessageTemplate.objects.create(
            organization=request.auth.organization,
            created_by=request.auth,
            media_type=MessageTemplate.MediaType.TEXT,
            **data.dict()
        )
        return 201, template
    except Exception as e:
        return 400, GenericErrorSchema(detail='Erro ao criar template')

@router.post('/media', response={201: MessageTemplateOut, 400: GenericErrorSchema})
def create_media_template(
    request, 
    title: str = Form(...), 
    shortcut: str = Form(''), 
    content: str = Form(''), 
    media_type: str = Form(...), 
    file: UploadedFile = File(...)
    ):
    
    mime = file.content_type or 'application/octet-stream'
    ext = mime.split('/')[-1].split(';')[0]
    path = default_storage.save(
        f'templates/{uuid.uuid4()}.{ext}',
        ContentFile(file.read())
    )
    url = default_storage.url(path)

    try:
        template = MessageTemplate.objects.create(
            organization=request.auth.organization,
            created_by=request.auth,
            title=title,
            shortcut=shortcut,
            content=content,
            media_type=media_type,
            file_url=url,
            mime_type=mime
        )
        return 201, template
    except Exception as e:
        return 400, GenericErrorSchema(detail='Creation template error')


@router.patch('/{template_id}', response={200: MessageTemplateOut, 404: GenericErrorSchema})
def update_template(request, template_id: int, data: MessageTemplateIn):
    try:
        template = MessageTemplate.objects.get(id=template_id, organization=request.auth.organization)
    except MessageTemplate.DoesNotExist:
        return 404, GenericErrorSchema(detail='Not found')
    
    for attr, value in data.dict().items():
        setattr(template, attr, value)

    template.save()
    return 200, template

@router.delete('/{template_id}', response={204: None, 404: GenericErrorSchema})
def delete_template(request, template_id: int):
    try:
        template = MessageTemplate.objects.get(id=template_id, organization=request.auth.organization)
    except MessageTemplate.DoesNotExist:
        return 404, GenericErrorSchema(detail='Not found')

    template.delete()
    return 204, None



