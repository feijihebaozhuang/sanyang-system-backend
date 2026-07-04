#!/usr/bin/env python3
from app import app
from core.provider_manager import ProviderManager
from extensions.ext_model_runtime import model_runtime

TENANT = "dbb18920-b55e-42db-9148-18d20a0baa3a"

with app.app_context():
    pm = ProviderManager(model_runtime)
    configs = pm.get_configurations(TENANT)
    names = []
    for cfg in configs.values():
        names.append(cfg.provider.provider)
    print("configured:", sorted(names))
    deep = [n for n in names if "deep" in n.lower()]
    print("deep:", deep)
    try:
        pm.get_model_type_instance(TENANT, "deepseek", "llm")
        print("deepseek llm: ok")
    except Exception as e:
        print("deepseek llm:", type(e).__name__, e)
