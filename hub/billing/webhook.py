import logging
import stripe
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from . import services

logger = logging.getLogger(__name__)


@csrf_exempt
def stripe_webhook(request: HttpRequest):
    if request.method != 'POST':
        return HttpResponse(status=405)

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f'Stripe webhook payload inválido: {e}')
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f'Stripe webhook assinatura inválida: {e}')
        return HttpResponse(status=400)

    event_type = event['type']
    data = event['data']['object']
    logger.info(f'Stripe event: {event_type}')

    if event_type in ('customer.subscription.updated', 'customer.subscription.created'):
        services.handle_subscription_updated(data)
    elif event_type == 'customer.subscription.deleted':
        services.handle_subscription_deleted(data)

    return HttpResponse({'status': 'ok'}, content_type='application/json', status=200)
