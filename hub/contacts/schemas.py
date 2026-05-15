from labels.schemas import LabelOut
from ninja import Schema
from typing import Optional
from datetime import datetime

#* ----- Contacts -----

class ContactIn(Schema):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    custom_fields: dict = {}
    pipedrive_person_id: Optional[int] = None

class ContactOut(Schema):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    custom_fields: dict
    created_at: datetime
    labels: list[LabelOut] = []

    @staticmethod
    def resolve_labels(obj):
        return obj.labels.all()

class ImportErrorOut(Schema):
    row: int
    reason: str

class ImportResultOut(Schema):
    created: int
    skipped: int
    errors: list[ImportErrorOut]

#* ----- Annotations -----

class AnnotationOut(Schema):
    id: int
    content: str
    pinned: bool
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_created_by_name(obj):
        return obj.created_by_name if obj.created_by_id and obj.created_by else None

class AnnotationCreateIn(Schema):
    content: str
    pinned: bool = False

class AnnotationUpdateIn(Schema):
    content: Optional[str] = None
    pinned: Optional[bool] = None

