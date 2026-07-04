#!/usr/bin/env python3
import json
import uuid

from app import app
from core.helper import encrypter
from extensions.ext_database import db
from models.provider import ProviderCredential, ProviderModel

TENANT = "dbb18920-b55e-42db-9148-18d20a0baa3a"
KEY = "sk-abaf056a56e745b396f0b7937ea503bb"

with app.app_context():
    enc = encrypter.encrypt_token(
        tenant_id=TENANT, token=json.dumps({"api_key": KEY})
    )
    row = (
        db.session.query(ProviderCredential)
        .filter_by(tenant_id=TENANT, provider_name="deepseek")
        .first()
    )
    if row:
        row.encrypted_config = enc
        row.credential_name = "default"
        cred_id = row.id
    else:
        row = ProviderCredential(
            tenant_id=TENANT,
            provider_name="deepseek",
            credential_name="default",
            encrypted_config=enc,
        )
        db.session.add(row)
        db.session.flush()
        cred_id = row.id
    for name in ("deepseek-chat", "deepseek-v4-flash"):
        if (
            not db.session.query(ProviderModel)
            .filter_by(tenant_id=TENANT, provider_name="deepseek", model_name=name)
            .first()
        ):
            db.session.add(
                ProviderModel(
                    tenant_id=TENANT,
                    provider_name="deepseek",
                    model_name=name,
                    model_type="llm",
                    credential_id=cred_id,
                    is_valid=True,
                )
            )
    db.session.commit()
    print("deepseek provider ok", cred_id)
