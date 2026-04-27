from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

@shared_task(bind=True, max_retries=3)
def send_invite_email(self, invite_id: int):
    from .models import Invite

    try:
        invite = Invite.objects.select_related('organization', 'invited_by').get(id=invite_id)
        invite_url = f'{settings.FRONTEND_URL}/invite/{invite.token}'
        org_name = invite.organization.name
        invited_by_name = (invite.invited_by.name or invite.invited_by.email) if invite.invited_by else org_name

        subject = f'Você foi convidado para {org_name}'

        text_content = (
            f'{invited_by_name} convidou você para entrar em {org_name}.\n'
            f'Acesse o link para aceitar: {invite_url}\n'
            f'Este convite expira em 7 dias.'
        )

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
            <h2 style="color: #111827;">Você foi convidado!</h2>
            <p style="color: #374151;">
                <strong>{invited_by_name}</strong> convidou você para fazer parte de
                <strong>{org_name}</strong>.
            </p>
            <p style="color: #374151;">Clique no botão abaixo para aceitar o convite:</p>
            <a href="{invite_url}"
               style="background-color: #4F46E5; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 6px; display: inline-block; margin: 16px 0;">
                Aceitar convite
            </a>
            <p style="color: #6B7280; font-size: 13px; margin-top: 24px;">
                Este convite expira em 7 dias.
            </p>
            <p style="color: #6B7280; font-size: 13px;">
                Se você não esperava este convite, ignore este e-mail.
            </p>
        </body>
        </html>
        """

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[invite.email],
        )
        email.attach_alternative(html_content, 'text/html')
        email.send()

    except Invite.DoesNotExist:
        return
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

