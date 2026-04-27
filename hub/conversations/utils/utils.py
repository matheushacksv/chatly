from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import base64
import uuid


def upload_attachment(base64_data: str, mime_type: str, folder: str = 'attachments') -> str:
    if ',' in base64_data:
        base64_data = base64_data.split(',')[1]

    file_bytes = base64.b64decode(base64_data)
    extension = mime_type.split('/')[-1].split(';')[0]
    file_name =  f'{folder}/{uuid.uuid4()}.{extension}'

    path = default_storage.save(file_name, ContentFile(file_bytes))
    return default_storage.url(path)

