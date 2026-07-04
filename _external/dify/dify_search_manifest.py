#!/usr/bin/env python3
import httpx
from configs import dify_config

base = str(dify_config.MARKETPLACE_API_URL).rstrip("/")
r = httpx.get(
    base + "/api/v1/dist/plugins/manifest.json",
    headers={"X-Dify-Version": dify_config.project.version},
    timeout=120,
    follow_redirects=True,
)
r.raise_for_status()
plugins = r.json().get("plugins", [])
hits = [p for p in plugins if "deepseek" in str(p).lower()]
print("total", len(plugins), "hits", len(hits))
for p in hits[:10]:
    print(p.get("plugin_id"), p.get("latest_package_identifier"))
