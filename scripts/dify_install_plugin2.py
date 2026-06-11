#!/usr/bin/env python3
"""Download DeepSeek plugin from marketplace and install."""
import json
import time

import httpx
from app import app
from configs import dify_config
from core.helper import encrypter, marketplace
from core.plugin.entities.plugin import PluginInstallationSource
from core.plugin.entities.plugin_daemon import PluginInstallTaskStatus
from core.plugin.impl.plugin import PluginInstaller
from extensions.ext_database import db
from models.provider import ProviderCredential, ProviderModel

TENANT = "dbb18920-b55e-42db-9148-18d20a0baa3a"
PLUGIN_ID = "langgenius/deepseek"
PROVIDER_NAME = "langgenius/deepseek/deepseek"
KEY = "sk-abaf056a56e745b396f0b7937ea503bb"


def wait_task(installer: PluginInstaller, task_id: str) -> bool:
    for _ in range(60):
        task = installer.fetch_plugin_installation_task(TENANT, task_id)
        print("status:", task.status)
        if task.status == PluginInstallTaskStatus.Success:
            return True
        if task.status == PluginInstallTaskStatus.Failed:
            return False
        time.sleep(3)
    return False


def resolve_identifier() -> str:
    decls = marketplace.batch_fetch_plugin_manifests([PLUGIN_ID])
    if decls:
        uid = decls[0].latest_package_identifier
        print("from batch manifests:", uid)
        return uid
    raw = marketplace.batch_fetch_plugin_by_ids([PLUGIN_ID])
    print("batch raw:", json.dumps(raw, ensure_ascii=False)[:800])
    if raw:
        p0 = raw[0]
        uid = p0.get("latest_package_identifier") or p0.get("plugin_unique_identifier")
        if uid:
            print("from batch raw:", uid)
            return uid
    base = str(dify_config.MARKETPLACE_API_URL).rstrip("/")
    url = base + "/api/v1/dist/plugins/manifest.json"
    r = httpx.get(
        url,
        headers={"X-Dify-Version": dify_config.project.version},
        timeout=60,
        follow_redirects=True,
    )
    r.raise_for_status()
    for p in r.json().get("plugins", []):
        pid = p.get("plugin_id")
        if pid == PLUGIN_ID or pid == "langgenius/deepseek":
            uid = p.get("latest_package_identifier") or p.get("latest_version_identifier")
            print("from manifest:", uid)
            return uid
    raise SystemExit("deepseek not found in marketplace manifest")


def install_uid(uid: str):
    installer = PluginInstaller()
    pkg = marketplace.download_plugin_pkg(uid)
    print("pkg bytes", len(pkg))
    dec = installer.upload_pkg(TENANT, pkg, verify_signature=False)
    print("uploaded", dec.unique_identifier)
    resp = installer.install_from_identifiers(
        TENANT,
        [dec.unique_identifier],
        PluginInstallationSource.Package,
        [{}],
    )
    print("task", resp.task_id)
    if not wait_task(installer, resp.task_id):
        raise SystemExit("install task failed")
    return dec.unique_identifier


def set_credentials(provider_name: str):
    enc = encrypter.encrypt_token(
        tenant_id=TENANT, token=json.dumps({"api_key": KEY})
    )
    row = (
        db.session.query(ProviderCredential)
        .filter_by(tenant_id=TENANT, provider_name=provider_name)
        .first()
    )
    if not row:
        row = ProviderCredential(
            tenant_id=TENANT,
            provider_name=provider_name,
            credential_name="default",
            encrypted_config=enc,
        )
        db.session.add(row)
    else:
        row.encrypted_config = enc
    db.session.flush()
    cred_id = row.id
    for name in ("deepseek-chat", "deepseek-v4-flash"):
        if (
            not db.session.query(ProviderModel)
            .filter_by(tenant_id=TENANT, provider_name=provider_name, model_name=name)
            .first()
        ):
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
    print("credentials saved")


with app.app_context():
    uid = resolve_identifier()
    install_uid(uid)
    set_credentials(PROVIDER_NAME)
    from core.plugin.impl.model_runtime_factory import create_plugin_provider_manager

    pm = create_plugin_provider_manager(tenant_id=TENANT)
    print("providers:", sorted(pm.get_configurations(TENANT).keys()))
