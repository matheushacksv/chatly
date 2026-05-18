from typing import Optional
import httpx

#* ----- Pipedrive Services -----

V2_BASE_URL = 'https://api.pipedrive.com/api/v2'

def _h(api_key: str) -> dict:
    return {'x-api-token': api_key}

def validate_integration(api_key):
    '''Valida a integração via API'''

    try:
        resp = httpx.get(
            'https://api.pipedrive.com/v1/users/me',
            params={'api_token': api_key},
            timeout=10
        )
        if resp.status_code != 200 or not resp.json().get('success'):
            return False
        else:
            return True
    except httpx.RequestError:
        return False

def pipeline_with_stages(api_key: str) -> list[dict]:
    '''Retorna funis com etapas'''

    try:
        pipelines = []
        cursor = None
        while True:
            params = {'limit': 100}
            if cursor:
                params['cursor'] = cursor
            resp = httpx.get(
                f'{V2_BASE_URL}/pipelines',
                params=params, headers=_h(api_key), timeout=10
            )
            body = resp.json()
            pipelines.extend(body.get('data') or [])
            cursor = (body.get('additional_data') or {}).get('next_cursor')
            if not cursor:
                break

        stages_resp = httpx.get(
            f'{V2_BASE_URL}/stages',
            headers=_h(api_key), timeout=10
        )

        stages = stages_resp.json().get('data') or []

        for p in pipelines:
            p['stages'] = [
                {'id': s['id'], 'name': s['name']}
                for s in stages
                if s['pipeline_id'] == p['id'] and not s.get('is_deleted')
            ]
        return pipelines
    except httpx.RequestError:
        return []


def _find_existing_person(api_key: str, contact) -> Optional[int]:
    '''Busca Person existente no Pipedrive por telefone ou email. Retorna id ou None.'''
    for term in filter(None, [contact.phone, contact.email]):
        resp = httpx.get(
            f'{V2_BASE_URL}/persons/search',
            headers=_h(api_key),
            params={'term': term, 'limit': 1},
            timeout=10,
        )
        items = (resp.json().get('data') or {}).get('items') or []
        if items:
            return items[0]['item']['id']
    return None


def create_or_update_person(api_key: str, contact) -> Optional[int]:
    '''Cria ou atualiza Person no Pipedrive. Retorna pipedrive_person_id'''

    payload = {'name': contact.name}
    if contact.phone:
        payload['phones'] = [{'value': contact.phone, 'primary': True}]
    if contact.email:
        payload['emails'] = [{'value': contact.email, 'primary': True}]

    if contact.pipedrive_person_id:
        # já vinculado — só atualiza
        resp = httpx.patch(
            f'{V2_BASE_URL}/persons/{contact.pipedrive_person_id}',
            headers=_h(api_key), json=payload, timeout=10
        )
        data = resp.json().get('data')
        return data['id'] if data else None

    # sem vínculo — busca por telefone/email antes de criar
    existing_id = _find_existing_person(api_key, contact)
    if existing_id:
        resp = httpx.patch(
            f'{V2_BASE_URL}/persons/{existing_id}',
            headers=_h(api_key), json=payload, timeout=10
        )
        data = resp.json().get('data')
        return data['id'] if data else existing_id

    resp = httpx.post(
        f'{V2_BASE_URL}/persons',
        headers=_h(api_key), json=payload, timeout=10
    )
    data = resp.json().get('data')
    return data['id'] if data else None

def create_deal(api_key: str, title: str, person_id: int, pipeline_id: int, stage_id: int) -> Optional[int]:
    '''Cria deal no Pipedrive, retorna deal_id'''

    resp = httpx.post(
        f'{V2_BASE_URL}/deals',
        headers=_h(api_key),
        json={
            'title': title,
            'person_id': person_id,
            'pipeline_id': pipeline_id,
            'stage_id': stage_id,
            'status': 'open',
        }, timeout=10
    )

    data = resp.json().get('data')
    return data['id'] if data else None

def close_deal(api_key: str, deal_id: int, won: bool = True) -> bool:
    '''Marca o deal como won ou lost'''
    resp = httpx.patch(
        f'{V2_BASE_URL}/deals/{deal_id}',
        headers=_h(api_key),
        json={'status': 'won' if won else 'lost'},
        timeout=10
    )
    return resp.json().get('success', False)


def create_note(api_key: str, deal_id: int, content: str, pinned: bool = False):
    '''Cria uma anotação no deal no Pipedrive'''
    resp = httpx.post(
        'https://api.pipedrive.com/v1/notes',
        params={'api_token': api_key},
        json={
            'deal_id': deal_id,
            'content': content,
            'pinned_to_deal_flag': 1 if pinned else 0,
        }, timeout=10
    )
    data = resp.json().get('data')
    return data['id'] if data else None

def get_notes(api_key: str, deal_id: int):
    '''Retorna as notas do deal no Pipedrive'''
    resp = httpx.get(
        'https://api.pipedrive.com/v1/notes',
        params={
            'api_token': api_key,
            'deal_id': deal_id
        }, timeout=10
    )
    data = resp.json().get('data')
    return data if data else None

def get_deal(api_key:str, deal_id:int) -> Optional[dict]:
    '''Retorna dados do deal: title, status, stage, pipeline'''

    resp = httpx.get(f'{V2_BASE_URL}/deals/{deal_id}', headers=_h(api_key), timeout=10)
    return resp.json().get('data')

def update_deal_stage(api_key:str, deal_id:int, stage_id:int) -> bool:
    '''Move deal para nova etapa'''
    resp = httpx.patch(
        f'{V2_BASE_URL}/deals/{deal_id}',
        headers=_h(api_key),
        json={'stage_id': stage_id},
        timeout=10
    )
    return resp.json().get('data') is not None

def get_activities(api_key:str, deal_id:int) -> list:
    '''Retorna atividades pendentes do deal (v1 api)'''
    resp = httpx.get(
        'https://api.pipedrive.com/v1/activities',
        params={'api_token': api_key, 'deal_id': deal_id, 'done': 0, 'limit': 20},
        timeout=10
    )
    return resp.json().get('data') or []

def mark_activity_done(api_token:str, activity_id:int) -> bool:
    '''Marca atividade como concluida'''
    resp = httpx.patch(
        f'{V2_BASE_URL}/activities/{activity_id}',
        headers=_h(api_token),
        json={'done': True},
        timeout=10
    )
    return resp.json().get('success', False)

def search_persons(api_token: str, term: str, limit: int = 20) -> list[dict]:
    '''Busca pessoas no Pipedrive por nome ou telefone. Retorna id, name, phone, email'''

    resp = httpx.get(
        f'{V2_BASE_URL}/persons/search',
        headers=_h(api_token),
        params={'term': term, 'fields': 'name,phone', 'limit': limit},
        timeout=10
    )
    items = (resp.json().get('data') or {}).get('items') or []
    result = []
    for it in items:
        p = it.get('item') or {}
        phones = p.get('phones') or []
        emails = p.get('emails') or []
        result.append(
            {'pipedrive_person_id': p.get('id'),
            'name': p.get('name') or '',
            'phone': phones[0] if phones else '',
            'email': emails[0] if emails else ''
            }
        )
    return result

def deal_fields(api_key: str) -> list[dict]:
    '''Lista campos do Deal (inclui personalizados). Retorna [{key, name}]'''

    fields = []
    cursor = None
    while True:
        params = {'limit': 500}
        if cursor:
            params['cursor'] = cursor
        resp = httpx.get(
            f'{V2_BASE_URL}/dealFields',
            params=params,
            headers=_h(api_key),
            timeout=10
        )
        body = resp.json()
        fields.extend(body.get('data') or [])
        cursor = (body.get('additional_data') or {}).get('next_cursor')
        if not cursor:
            break
    return [{'key': f['field_code'], 'name': f['field_name']}
            for f in fields
            if f.get('is_custom_field') and f.get('is_writable')]

def update_deal_fields(api_key: str, deal_id: int, fields: dict) -> bool:
    '''Patch custom fields do deal'''

    resp = httpx.patch(
        f'{V2_BASE_URL}/deals/{deal_id}',
        headers=_h(api_key),
        json={'custom_fields': fields},
        timeout=10
    )
    return resp.json().get('data') is not None


