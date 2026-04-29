from integrations.models import PipedriveIntegration
from django.db import IntegrityError
from ninja import Router, File, UploadedFile, Query

from .models import Contact, ContactAnnotation
from .schemas import ContactIn, ContactOut, AnnotationUpdateIn, AnnotationCreateIn, AnnotationOut, ImportResultOut
from labels.schemas import SetLabelsIn
from core.utils.errors import GenericErrorSchema
from django.shortcuts import get_object_or_404
from typing import Optional
import csv, io
from integrations.pipedrive_tasks import sync_contact_to_pipedrive, sync_annotation_to_pipedrive

router = Router(tags=['Contacts'])

#* ----- Contacts -----

@router.get('/', response=list[ContactOut])
def list_contacts(request, label_id: Optional[int] = Query(None), limit: int = Query(500), offset: int = Query(0)):
    qs = Contact.objects.filter(organization=request.auth.organization)
    if label_id:
        qs = qs.filter(labels__id=label_id)
    return list(qs.prefetch_related('labels').order_by('-created_at')[offset:offset + limit])

@router.post('/import', response={200: ImportResultOut})
def import_contacts(request, file: UploadedFile = File(...)):

    user = request.auth
    org = user.organization

    content = file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))

    valid_rows = []
    errors = []
    reserved = {'name', 'phone', 'email'}

    for i, row in enumerate(reader, start=2):
        name = row.get('name', '').strip()
        phone = row.get('phone', '').strip()
        email = row.get('email', '').strip() or None

        if not name:
            errors.append({'row': i, 'reason': 'Nome obrigatório'})
            continue
        if not phone:
            errors.append({'row': i, 'reason': 'Telefone obrigatório'})
            continue

        valid_rows.append({
            'name': name,
            'phone': phone,
            'email': email,
            'custom_fields': {k: v for k, v in row.items() if k not in reserved and v},
        })

    if not valid_rows:
        return {'created': 0, 'skipped': 0, 'errors': errors}

    existing_phones = set(
        Contact.objects.filter(
            organization=org,
            phone__in=[r['phone'] for r in valid_rows],
        ).values_list('phone', flat=True)
    )

    to_create = [
        Contact(organization=org, **r)
        for r in valid_rows
        if r['phone'] not in existing_phones
    ]
    skipped = len(valid_rows) - len(to_create)

    Contact.objects.bulk_create(to_create, ignore_conflicts=True)
    created = len(to_create)

    if created and PipedriveIntegration.objects.filter(organization=org, is_active=True).exists():
        new_ids = Contact.objects.filter(
            organization=org,
            phone__in=[c.phone for c in to_create],
        ).values_list('id', flat=True)
        for contact_id in new_ids:
            sync_contact_to_pipedrive.delay(contact_id)

    return {'created': created, 'skipped': skipped, 'errors': errors}

@router.get('/{contact_id}', response={200: ContactOut, 404: GenericErrorSchema})
def get_contact(request, contact_id: int):
    try:
        return Contact.objects.get(id=contact_id, organization=request.auth.organization)
    except Contact.DoesNotExist:
        return 404, {'detail': 'Contact not found'}

@router.post('/', response={201: ContactOut, 400: GenericErrorSchema})
def create_contact(request, data: ContactIn):

    from billing.services import check_contact_limit

    if not check_contact_limit(request.auth.organization):
        return 400, GenericErrorSchema(detail='Limite de contatos atingido no plano atual')

    if data.phone and Contact.objects.filter(organization=request.auth.organization, phone=data.phone).exists():
        return 400, {'detail': 'Phone already registered'}

    contact = Contact.objects.create(organization=request.auth.organization, **data.dict())

    if PipedriveIntegration.objects.filter(organization=request.auth.organization, is_active=True).exists():
        sync_contact_to_pipedrive.delay(contact.id)
    return 201, contact

@router.patch('/{contact_id}', response={200: ContactOut, 400: GenericErrorSchema})
def update_contact(request, contact_id: int, data: ContactIn):
    try:
        contact = Contact.objects.get(id=contact_id, organization=request.auth.organization)
    except Contact.DoesNotExist:
        return 404, {'detail': 'Contact not found'}

    for field, value in data.dict(exclude_none=True).items():
        setattr(contact, field, value)
    contact.save()

    if PipedriveIntegration.objects.filter(organization=request.auth.organization, is_active=True).exists():
        sync_contact_to_pipedrive.delay(contact.id)
    return contact

@router.post('/{contact_id}/labels', response={200: ContactOut})
def set_contact_labels(request, contact_id: int, data: SetLabelsIn):
    from conversations.models import Conversation
    contact = get_object_or_404(Contact, id=contact_id, organization=request.auth.organization)
    contact.labels.set(data.label_ids)
    for conv in Conversation.objects.filter(contact=contact, organization=request.auth.organization, status=Conversation.Status.OPEN):
        conv.labels.set(data.label_ids)
    return contact

@router.delete('/{contact_id}', response={204: None, 404: GenericErrorSchema})
def delete_contact(request, contact_id: int):
    try:
        contact = Contact.objects.get(id=contact_id, organization=request.auth.organization)
    except Contact.DoesNotExist:
        return 404, {'detail': 'Contact not found'}

    contact.delete()
    return 204, None

#* ----- Annotations -----

@router.get('/{contact_id}/annotations', response=list[AnnotationOut])
def list_annotations(request, contact_id: int):
    contact = get_object_or_404(Contact, id=contact_id, organization=request.auth.organization)
    return contact.annotations.select_related('created_by').all()

@router.post('/{contact_id}/annotations', response={201: AnnotationOut})
def create_annotation(request, contact_id: int, data: AnnotationCreateIn):
    contact = get_object_or_404(Contact, id=contact_id, organization=request.auth.organization)

    annotation = ContactAnnotation.objects.create(
        organization=request.auth.organization,
        contact=contact,
        created_by=request.auth,
        **data.dict()
    )

    if PipedriveIntegration.objects.filter(organization=request.auth.organization, is_active=True).exists():
        sync_annotation_to_pipedrive(annotation.id)

    return 201, annotation
    
@router.patch('/{contact_id}/annotations/{ann_id}', response={200: AnnotationOut})
def update_annotation(request, contact_id: int, ann_id: int, data: AnnotationUpdateIn):
    ann = get_object_or_404(ContactAnnotation, id=ann_id, contact_id=contact_id, organization=request.auth.organization)

    for field, value in data.dict(exclude_none=True).items():
        setattr(ann, field, value)
    ann.save()
    return ann

@router.delete('/{contact_id}/annotations/{ann_id}', response={204: None})
def delete_annotation(request, contact_id: int, ann_id: int):
    ann = get_object_or_404(ContactAnnotation, id=ann_id, contact_id=contact_id, organization=request.auth.organization)

    ann.delete()
    return 204, None


