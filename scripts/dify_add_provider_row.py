#!/usr/bin/env python3
import uuid

from app import app
from extensions.ext_database import db
from models.provider import Provider, ProviderCredential

TENANT = "dbb18920-b55e-42db-9148-18d20a0baa3a"
CRED_ID = "019e4d4f-957e-768f-8f45-6ffae2433cd9"

with app.app_context():
    cred = (
        db.session.query(ProviderCredential)
        .filter_by(tenant_id=TENANT, provider_name="deepseek")
        .first()
    )
    if not cred:
        print("no credential")
        raise SystemExit(1)
    cred_id = str(cred.id)
    row = (
        db.session.query(Provider)
        .filter_by(tenant_id=TENANT, provider_name="deepseek")
        .first()
    )
    if row:
        row.is_valid = True
        row.credential_id = cred_id
        row.provider_type = "custom"
        print("updated provider", row.id)
    else:
        row = Provider(
            tenant_id=TENANT,
            provider_name="deepseek",
            provider_type="custom",
            is_valid=True,
            credential_id=cred_id,
        )
        db.session.add(row)
        print("created provider")
    db.session.commit()
    print("ok", cred_id)
