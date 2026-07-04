#!/usr/bin/env python3
from app import app
from core.plugin.impl.model_runtime_factory import create_plugin_provider_manager

TENANT = "dbb18920-b55e-42db-9148-18d20a0baa3a"
with app.app_context():
    pm = create_plugin_provider_manager(tenant_id=TENANT)
    configs = pm.get_configurations(TENANT)
    for name, cfg in configs.items():
        if "deep" in name.lower():
            print("provider:", name, "custom:", cfg.is_custom_configured())
