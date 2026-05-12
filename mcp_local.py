import sys, json, ssl, urllib.request

URL = "https://8.163.107.156:18789/mcp"
AUTH = "Bearer sanyang-mcp-token-a3fc681da4c543754663e78eb960eceb"
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

        data = json.dumps(req).encode()
        headers = {"Authorization": AUTH, "Content-Type": "application/json"}
        r = urllib.request.Request(URL, data=data, headers=headers, method="POST")
        resp = urllib.request.urlopen(r, context=CTX)
        print(json.dumps(json.loads(resp.read())), flush=True)
    except Exception as e:
        print(json.dumps({"jsonrpc":"2.0","error":{"code":-32603,"message":str(e)},"id":rid}), flush=True)