#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署后检查 3002/3003 是否注册 /api/mp 路由（POST 不应 404/405）。"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def _post(url: str) -> int:
    req = urllib.request.Request(
        url,
        data=b'{"code":"verify"}',
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def main() -> int:
    bad = []
    for port, label in ((3002, "production"), (3003, "customer-order")):
        code = _post(f"http://127.0.0.1:{port}/api/mp/cs/wx/login")
        if code in (404, 405):
            bad.append(f":{port} ({label}) POST /api/mp/cs/wx/login -> HTTP {code}")
        elif code >= 500:
            bad.append(f":{port} ({label}) HTTP {code}")
    if bad:
        print("MP API 未就绪:")
        for line in bad:
            print(" ", line)
        print("修复: git pull && bash deploy.sh && bash deploy/install-feijihe-mp-proxy.sh")
        return 1
    print("MP API OK (3002/3003 已响应 POST /api/mp/cs/wx/login)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
