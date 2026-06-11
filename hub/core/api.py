from ninja import NinjaAPI
from ninja_jwt.authentication import JWTAuth

# Imports routers
from accounts.api import router as accounts_router
from accounts.org_api import router as org_router
from agents.api import router as agents_router
from integrations.api import router as integrations_router
from conversations.api import router as conversations_router
from integrations.webhook import router as webhook_router
from integrations.pipedrive_webhook import router as pipedrive_webhook_router
from contacts.api import router as contact_router
from contacts.public_api import router as public_router
from templates.api import router as templates_router
from labels.api import router as labels_router
from campaigns.api import router as campaigns_router
from billing.api import router as billing_router, admin_router as billing_admin_router
from automations.api import router as automations_router

api = NinjaAPI(auth=JWTAuth())

# Add routers
api.add_router('auth/', accounts_router)
api.add_router('org/', org_router)
api.add_router('agents/', agents_router)
api.add_router('integrations/whatsapp/', integrations_router)
api.add_router('conversations/', conversations_router)
api.add_router('webhooks/whatsapp/', webhook_router)
api.add_router('webhooks/pipedrive/', pipedrive_webhook_router)
api.add_router('contacts/', contact_router),
api.add_router('public/', public_router)
api.add_router('templates/', templates_router)
api.add_router('labels/', labels_router)
api.add_router('campaigns/', campaigns_router)
api.add_router('billing/', billing_router)
api.add_router('admin/billing/', billing_admin_router)
api.add_router('automations/', automations_router)