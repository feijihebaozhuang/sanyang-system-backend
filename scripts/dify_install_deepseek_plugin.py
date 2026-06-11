#!/usr/bin/env python3
"""Install DeepSeek model plugin and configure API key (run in docker-api-1)."""
import json
import time

from app import app
from core.helper import encrypter
from core.plugin.entities.plugin import PluginInstallationSource
from core.plugin.entities.plugin_daemon import PluginInstallTaskStatus
from core.plugin.impl.plugin import PluginInstaller
from extensions.ext_database import db
from models.provider import ProviderCredential, ProviderModel

TENANT = "dbb18920-b55e-42db-9148-18d20a0baa3a"
PROVIDER = "langgenius/deepseek/deepseek"
KEY = "sk-abaf056a56e745b396f0b7937ea503bb"
# marketplace identifier often includes version; try common forms
IDENTIFIERS = [
    "langgenius/deepseek/deepseek",
    "langgenius/deepseek/deepseek:latest",
]


def wait_task(installer: PluginInstaller, task_id: str, timeout: int = 180) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = installer.fetch_plugin_installation_task(TENANT, task_id)
        st = task.status
        print("task", task_id, st)
        if st in (PluginInstallTaskStatus.Success, PluginInstallTaskStatus.Failed):
            return st == PluginInstallTaskStatus.Success
        time.sleep(3)
    return False


def install_plugin(installer: PluginInstaller) -> str:
    for ident in IDENTIFIERS:
        try:
            dec = installer.decode_plugin_from_identifier(TENANT, ident)
            uid = dec.unique_identifier
            print("decoded", ident, "->", uid)
            ident = uid
        except Exception as e:
            print("decode skip", ident, e)
            continue
        try:
            resp = installer.install_from_identifiers(
                TENANT,
                [ident],
                PluginInstallationSource.Marketplace,
                [{}],
            )
            print("install started", resp.task_id)
            if wait_task(installer, resp.task_id):
                return ident
        except Exception as e:
            print("install fail", ident, e)
    raise SystemExit("plugin install failed")


def set_credentials(provider_name: str):
    enc = encrypter.encrypt_token(
        tenant_id=TENANT, token=json.dumps({"api_key": KEY})
    )
    row = (
        db.session.query(ProviderCredential)
        .filter_by(tenant_id=TENANT, provider_name=provider_name)
        .first()
    )
    if row:
        row.encrypted_config = enc
        cred_id = row.id
    else:
        row = ProviderCredential(
            tenant_id=TENANT,
            provider_name=provider_name,
            credential_name="default",
            encrypted_config=enc,
        )
        db.session.add(row)
        db.session.flush()
        cred_id = row.id
    for name in ("deepseek-chat", "deepseek-v4-flash"):
        pm = (
            db.session.query(ProviderModel)
            .filter_by(
                tenant_id=TENANT,
                provider_name=provider_name,
                model_name=name,
            )
            .first()
        )
        if not pm:
            db.session.add(
                ProviderModel(
                    tenant_id=TENANT,
                    provider_name=provider_name,
                    model_name=name,
                    model_type="llm",
                    credential_id=cred_id,
                    is_valid=True,
                )
            )
    db.session.commit()
    print("credentials ok for", provider_name)


with app.app_context():
    installer = PluginInstaller()
    plugins = installer.list_plugins(TENANT)
    print("installed plugins:", [p.plugin_id for p in plugins])
    if not any("deepseek" in (p.plugin_id or "") for p in plugins):
        install_plugin(installer)
    else:
        print("deepseek plugin already present")
    set_credentials(PROVIDER)
    from core.plugin.impl.model_runtime_factory import create_plugin_provider_manager

    pm = create_plugin_provider_manager(tenant_id=TENANT)
    configs = pm.get_configurations(TENANT)
    names = sorted(configs.keys())
    print("providers after install:", names)
