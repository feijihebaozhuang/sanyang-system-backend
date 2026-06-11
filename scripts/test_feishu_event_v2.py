#!/usr/bin/env python3
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.environ.setdefault("MYSQL_PASSWORD", "local-dev")

import feishu_dify as fd

payload = {
    "schema": "2.0",
    "header": {"event_id": "test-local-1", "event_type": "im.message.receive_v1"},
    "event": {
        "message": {
            "chat_type": "p2p",
            "chat_id": "oc_test",
            "message_type": "text",
            "content": json.dumps({"text": "hi"}),
        },
        "sender": {
            "sender_type": "user",
            "sender_id": {"open_id": "ou_0a6f33089481187f1a8df9c2b43296d8"},
        },
    },
}
raw = json.dumps(payload).encode()
body, code = fd.handle_webhook(raw, {})
print("handle:", code, body)
import time

time.sleep(15)
print("done wait")
