from ninja import Router
from .models import Label
from .schemas import LabelIn, LabelOut
from django.shortcuts import get_object_or_404
from core.utils.errors import GenericErrorSchema
from accounts.utils import has_permission


router = Router(tags=['Labels'])

@router.get('/', response=list[LabelOut])
def list_labels(request):
    return Label.objects.filter(organization=request.auth.organization).all()


@router.post('/', response={201: LabelOut, 400: GenericErrorSchema, 403: GenericErrorSchema})
def create_labels(request, data: LabelIn):
    
    if not has_permission(request.auth, 'add_label'):
        return 403, GenericErrorSchema(detail='No permission')

    try:
        label = Label.objects.create(
            name=data.name,
            color=data.color,
            organization=request.auth.organization
        )
        return 201, label
    except Exception as e:
        return GenericErrorSchema(f'Label creation error: {e}')
    

@router.patch('/{label_id}', response={200: LabelOut})
def update_label(request, label_id: int, data: LabelIn):

    if not has_permission(request.auth, 'add_label'):
        return 403, GenericErrorSchema(detail='No permission')

    label = get_object_or_404(Label, id=label_id, organization=request.auth.organization)

    label.name = data.name
    label.color = data.color
    label.save()

    return 200, label

@router.delete('/{label_id}', response={204: None})
def delete_label(request, label_id: int):

    if not has_permission(request.auth, 'add_label'):
        return 403, GenericErrorSchema(detail='No permission')    

    label = get_object_or_404(Label, id=label_id, organization=request.auth.organization)

    label.delete()

    return 204, None
