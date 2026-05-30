# -*- coding: utf-8 -*-
"""
MCP 客户端桥接层（已停用 – 原指向 156 服务器）。
156 已下线，此文件保留仅作历史参考，未被任何 service 引用。
如需重新启用，请修改 URL 指向新的 MCP 服务器地址。
"""
import sys, json, ssl, urllib.request

URL = ""  # 已停用
AUTH = ""
CTX = ssl._create_unverified_context()

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        req = json.loads(line)
        method = req.get("method")
        rid = req.get("id")

        if method == "initialize":
            result = {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "sanyang-mcp-server", "version": "1.0.0"}
            }
            print(json.dumps({"jsonrpc":"2.0","result":result,"id":rid}), flush=True)
            continue

        if method == "notifications/initialized":
            print(json.dumps({"jsonrpc":"2.0","result":None,"id":rid}), flush=True)
            continue

        if not URL:
            print(json.dumps({"jsonrpc":"2.0","error":{"code":-32000,"message":"MCP 已停用（原指向 156 服务器，已下线）"},"id":rid}), flush=True)
            continue

        data = json.dumps(req).encode()
        headers = {"Authorization": AUTH, "Content-Type": "application/json"}
        r = urllib.request.Request(URL, data=data, headers=headers, method="POST")
        resp = urllib.request.urlopen(r, context=CTX)
        print(json.dumps(json.loads(resp.read())), flush=True)
    except Exception as e:
        print(json.dumps({"jsonrpc":"2.0","error":{"code":-32603,"message":str(e)},"id":rid}), flush=True)
