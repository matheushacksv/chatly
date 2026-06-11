"""Regressão: gestão de convites pendentes — listar, revogar, reenviar.

Cobre o gap onde a org enviava convite mas não tinha como ver/cancelar os
pendentes. Endpoints em `accounts/org_api.py` (list/revoke/resend).
"""
import pytest
from datetime import timedelta

from django.test import Client
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken

from accounts.models import Organization, User, Invite


LIST_URL = '/api/org/invites'
ACCEPT_URL = '/api/auth/invite/accept'


def _invite(org, email='convidado@teste.com', accepted=False, days=7):
    return Invite.objects.create(
        organization=org,
        email=email,
        role=User.Role.MEMBER,
        expires_at=timezone.now() + timedelta(days=days),
        accepted=accepted,
    )


@pytest.fixture
def member_client(db, org):
    """Client de membro comum (não owner/admin) — deve bater em 403."""
    member = User.objects.create_user(
        email='membro@teste.com', password='senha123', name='Membro',
        organization=org, role=User.Role.MEMBER,
    )
    access = str(RefreshToken.for_user(member).access_token)
    return Client(headers={'authorization': f'Bearer {access}'})


# ---- LIST -------------------------------------------------------------------

@pytest.mark.django_db
def test_lista_so_pendentes_da_org(auth_client, org):
    _invite(org, email='a@teste.com')
    _invite(org, email='aceito@teste.com', accepted=True)  # não aparece
    other = Organization.objects.create(name='Outra', slug='outra')
    _invite(other, email='vaza@teste.com')  # de outra org, não aparece

    resp = auth_client.get(LIST_URL)
    assert resp.status_code == 200
    emails = [i['email'] for i in resp.json()]
    assert emails == ['a@teste.com']


@pytest.mark.django_db
def test_lista_marca_expirado(auth_client, org):
    _invite(org, email='vivo@teste.com', days=7)
    _invite(org, email='morto@teste.com', days=-1)  # já expirado

    by_email = {i['email']: i for i in auth_client.get(LIST_URL).json()}
    assert by_email['vivo@teste.com']['is_expired'] is False
    assert by_email['morto@teste.com']['is_expired'] is True


@pytest.mark.django_db
def test_membro_comum_nao_lista(member_client, org):
    _invite(org)
    assert member_client.get(LIST_URL).status_code == 403


# ---- REVOKE -----------------------------------------------------------------

@pytest.mark.django_db
def test_revoga_remove_e_invalida_token(auth_client, org):
    inv = _invite(org)
    token = str(inv.token)

    resp = auth_client.delete(f'{LIST_URL}/{inv.id}')
    assert resp.status_code == 204
    assert not Invite.objects.filter(id=inv.id).exists()

    # token revogado → accept dá 404 (get_object_or_404 não acha mais).
    accept = Client().post(
        ACCEPT_URL,
        data={'token': token, 'name': 'X', 'password': 'senha1234',
              'repeat_password': 'senha1234'},
        content_type='application/json',
    )
    assert accept.status_code == 404


@pytest.mark.django_db
def test_revoga_de_outra_org_404(auth_client, org):
    other = Organization.objects.create(name='Outra', slug='outra')
    inv = _invite(other)
    resp = auth_client.delete(f'{LIST_URL}/{inv.id}')
    assert resp.status_code == 404
    assert Invite.objects.filter(id=inv.id).exists()  # intacto


@pytest.mark.django_db
def test_membro_comum_nao_revoga(member_client, org):
    inv = _invite(org)
    assert member_client.delete(f'{LIST_URL}/{inv.id}').status_code == 403


# ---- RESEND -----------------------------------------------------------------

@pytest.mark.django_db
def test_resend_renova_expiracao_mantem_token(auth_client, org, mocker):
    send = mocker.patch('accounts.org_api.send_invite_email.delay')
    inv = _invite(org, days=-1)  # expirado
    old_exp, token = inv.expires_at, inv.token

    resp = auth_client.post(f'{LIST_URL}/{inv.id}/resend')
    assert resp.status_code == 200

    inv.refresh_from_db()
    assert inv.expires_at > old_exp       # renovado
    assert inv.expires_at > timezone.now()
    assert inv.token == token             # mesmo token
    send.assert_called_once_with(inv.id)  # reenfileira email


@pytest.mark.django_db
def test_resend_de_outra_org_404(auth_client, org, mocker):
    mocker.patch('accounts.org_api.send_invite_email.delay')
    other = Organization.objects.create(name='Outra', slug='outra')
    inv = _invite(other)
    assert auth_client.post(f'{LIST_URL}/{inv.id}/resend').status_code == 404


@pytest.mark.django_db
def test_membro_comum_nao_reenvia(member_client, org, mocker):
    mocker.patch('accounts.org_api.send_invite_email.delay')
    inv = _invite(org)
    assert member_client.post(f'{LIST_URL}/{inv.id}/resend').status_code == 403
