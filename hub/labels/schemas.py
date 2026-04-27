from ninja import Schema


class LabelIn(Schema):
    name: str
    color: str = '#6366f1'

class LabelOut(Schema):
    id: int
    name: str
    color: str

class SetLabelsIn(Schema):
    label_ids: list[int] = []
