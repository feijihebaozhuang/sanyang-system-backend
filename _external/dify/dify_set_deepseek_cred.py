#!/usr/bin/env python3
from app import app
from extensions.ext_database import db
from models.provider import ProviderCredential
from services.model_provider_service import ModelProviderService

TENANT = "dbb18920-b55e-42db-9148-18d20a0baa3a"
PROVIDER = "langgenius/deepseek/deepseek"
KEY = "sk-abaf056a56e745b396f0b7937ea503bb"

with app.app_context():
    svc = ModelProviderService()
    creds = {"api_key": KEY}
    svc.validate_provider_credentials(TENANT, PROVIDER, creds)
    print("validate ok")
    row = (
        db.session.query(ProviderCredential)
        .filter_by(tenant_id=TENANT, provider_name=PROVIDER)
        .first()
    )
    if row:
        svc.update_provider_credential(TENANT, PROVIDER, creds, str(row.id), None)
        svc.switch_active_provider_credential(TENANT, PROVIDER, str(row.id))
        print("updated", row.id)
    else:
        svc.create_provider_credential(TENANT, PROVIDER, creds, "feishu-bot")
        row = (
            db.session.query(ProviderCredential)
            .filter_by(tenant_id=TENANT, provider_name=PROVIDER)
            .order_by(ProviderCredential.created_at.desc())
            .first()
        )
        if row:
            svc.switch_active_provider_credential(TENANT, PROVIDER, str(row.id))
        print("created feishu-bot")
    pm = svc._get_provider_manager(TENANT)
    pm.clear_configurations_cache(TENANT)
    cfg = pm.get_configurations(TENANT).get(PROVIDER)
    print("available:", cfg.is_custom_configuration_available())
