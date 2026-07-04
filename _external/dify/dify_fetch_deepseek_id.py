#!/usr/bin/env python3
from core.helper import marketplace

plugins = marketplace.batch_fetch_plugin_by_ids(["langgenius/deepseek/deepseek"])
for p in plugins:
    print(p.get("plugin_id"), p.get("latest_version"), p.get("latest_package_identifier"))
