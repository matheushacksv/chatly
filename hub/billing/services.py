import stripe
from django.conf import settings
from django.utils import timezone

stripe.api_key = settings.STRIPE_SECRET_KEY

def get_free_plan():
    from billing.models import Plan
    return Plan.objects.get(slug='free')

def get_or_create_subscription(org):
    from billing.models import OrganizationSubscription
    
    sub, _ = OrganizationSubscription.objects.get_or_create(
        organization=org,
        defaults={'plan': get_free_plan()},
    )
    return sub

#* ----- Limit checks ------

def check_instance_limit(org) -> bool:
    from integrations.models import WhatsAppInstance

    sub = get_or_create_subscription(org)
    if sub.plan.is_unlimited or sub.plan.max_instances is None:
        return True
    current = WhatsAppInstance.objects.filter(organization=org).count()
    return current < sub.max_instances_total

def check_member_limit(org) -> bool:
    from accounts.models import User

    sub = get_or_create_subscription(org)
    if sub.plan.is_unlimited or sub.plan.max_members is None:
        return True
    current = User.objects.filter(organization=org, is_active=True).count()
    return current < sub.plan.max_members

def check_contact_limit(org) -> bool:
    from contacts.models import Contact

    sub = get_or_create_subscription(org)
    if sub.plan.is_unlimited or sub.plan.max_contacts is None:
        return True
    current = Contact.objects.filter(organization=org).count()
    return current < sub.plan.max_contacts

#* ----- Stripe ------

def get_or_create_stripe_customer(org, sub):
    if sub.stripe_customer_id:
        return sub.stripe_customer_id
    from accounts.models import User
    owner = User.objects.filter(organization=org, role='owner').first()
    customer = stripe.Customer.create(
        name=org.name,
        email=owner.email if owner else None,
        metadata={'org_id': org.id},
    )
    sub.stripe_customer_id = customer.id
    sub.save(update_fields=['stripe_customer_id'])
    return customer.id

def create_checkout_session(org, plan_slug, success_url, cancel_url):
    from billing.models import Plan

    plan = Plan.objects.get(slug=plan_slug, is_active=True)
    if not plan.stripe_price_id:
        raise ValueError('Plano sem stripe_price_id configurado')

    sub = get_or_create_subscription(org)
    customer_id = get_or_create_stripe_customer(org, sub)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode='subscription',
        line_items=[{'price': plan.stripe_price_id, 'quantity': 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={'org_id': org.id, 'plan_slug': plan.slug},
        subscription_data={
            'metadata': {'org_id': str(org.id), 'plan_slug': plan.slug},
        },
    )
    return session.url

def create_portal_session(org, return_url):
    sub = get_or_create_subscription(org)
    if not sub.stripe_customer_id:
        raise ValueError('Org sem customer Stripe')

    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=return_url
    )
    return session.url

def add_extra_instances(org, quantity: int):
    from billing.models import Plan
    sub = get_or_create_subscription(org)
    if not sub.stripe_subscription_id:
        raise ValueError('Org sem subscription Stripe ativa')
    plan = sub.plan
    if not plan.stripe_extra_instance_price_id:
        raise ValueError('Plano sem preço de instância extra configurado')
    stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
    existing_item = next(
        (i for i in stripe_sub['items']['data']
        if i['price']['id'] == plan.stripe_extra_instance_price_id),
        None
    )
    if existing_item:
        stripe.SubscriptionItem.modify(
            existing_item['id'],
            quantity=existing_item['quantity'] + quantity
        )
    else:
        stripe.SubscriptionItem.create(
            subscription=sub.stripe_subscription_id,
            price=plan.stripe_extra_instance_price_id,
            quantity=quantity,
        )
    sub.extra_instances += quantity
    sub.save(update_fields=['extra_instances'])

#* ----- Webhook handlers -----

def handle_subscription_updated(stripe_sub):
    from billing.models import OrganizationSubscription, Plan
    import datetime

    data = stripe_sub.to_dict() if hasattr(stripe_sub, 'to_dict') else dict(stripe_sub)

    stripe_sub_id = data['id']

    try:
        sub = OrganizationSubscription.objects.get(stripe_subscription_id=stripe_sub_id)
    except OrganizationSubscription.DoesNotExist:
        customer_id = data['customer']
        try:
            sub = OrganizationSubscription.objects.get(stripe_customer_id=customer_id)
        except OrganizationSubscription.DoesNotExist:
            return
        sub.stripe_subscription_id = stripe_sub_id

    metadata = data.get('metadata') or {}
    plan_slug = metadata.get('plan_slug')
    if plan_slug:
        try:
            sub.plan = Plan.objects.get(slug=plan_slug)
        except Plan.DoesNotExist:
            pass
    else:
        try:
            price_id = data['items']['data'][0]['price']['id']
            sub.plan = Plan.objects.get(stripe_price_id=price_id)
        except (KeyError, IndexError, Plan.DoesNotExist):
            pass

    stripe_status = data.get('status', '')
    cancel_at_period_end = data.get('cancel_at_period_end', False)
    cancel_at = data.get('cancel_at')

    scheduled_cancel = cancel_at_period_end or bool(cancel_at)

    if scheduled_cancel and stripe_status == 'active':
        sub.status = OrganizationSubscription.Status.CANCELED
    else:
        status_map = {
            'active': OrganizationSubscription.Status.ACTIVE,
            'past_due': OrganizationSubscription.Status.PAST_DUE,
            'canceled': OrganizationSubscription.Status.CANCELED,
            'trialing': OrganizationSubscription.Status.TRIALING,
        }
        sub.status = status_map.get(stripe_status, OrganizationSubscription.Status.FREE)

    period_end = data.get('current_period_end')
    if period_end:
        sub.current_period_end = datetime.datetime.fromtimestamp(period_end, tz=timezone.utc)
    sub.save()

def handle_subscription_deleted(stripe_sub):
    from billing.models import OrganizationSubscription
    data = stripe_sub.to_dict() if hasattr(stripe_sub, 'to_dict') else dict(stripe_sub)
    stripe_sub_id = data['id']

    try:
        sub = OrganizationSubscription.objects.get(stripe_subscription_id=stripe_sub_id)
        sub.plan = get_free_plan()
        sub.status = OrganizationSubscription.Status.CANCELED
        sub.stripe_subscription_id = None
        sub.extra_instances = 0
        sub.save()
    except OrganizationSubscription.DoesNotExist:
        pass


