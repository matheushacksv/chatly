"""Auth por API key da organização para a API pública (Bearer header).

Diferente do JWTAuth (que devolve um User), aqui `request.auth` é a própria
Organization resolvida pela `api_key`. Usado só no router público
(`contacts/public_api.py`).
"""
from ninja.security import HttpBearer

from accounts.models import Organization


class ApiKeyAuth(HttpBearer):
    def authenticate(self, request, token):
        if not token:
            return None
        return Organization.objects.filter(api_key=token).first()
