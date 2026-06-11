#!/usr/bin/env python3
from app import app
from core.plugin.impl.model_runtime_factory import create_plugin_provider_manager

TENANT = "dbb18920-b55e-42db-9148-18d20a0baa3a"

with app.app_context():
    pm = create_plugin_provider_manager(tenant_id=TENANT)
    configs = pm.get_configurations(TENANT)
    names = sorted(cfg.provider.provider for cfg in configs.values())
    print("providers:", names)
    print("deepseek in list:", "deepseek" in names)
    for n in names:
        if "deep" in n.lower():
            print("match:", n)
