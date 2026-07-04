# -*- coding: utf-8 -*-
"""飞书事件订阅 ↔ Dify 对话 API 桥接（Webhook 模式）。"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import threading
import time
import urllib.error
import urllib.request
from typing import Any

from settings import get_feishu_dify_config

_log = logging.getLogger(__name__)

_TENANT_TOKEN: dict[str, Any] = {"token": "", "expire_at": 0.0}
_CONV: dict[str, str] = {}
_SEEN_EVENTS: dict[str, float] = {}
_SEEN_MAX = 2000


def _cfg() -> dict[str, str]:
    return get_feishu_dify_config()


def is_enabled() -> bool:
    c = _cfg()
    return bool(
        c.get("enabled")
        and c.get("app_id")
        and c.get("app_secret")
        and c.get("dify_api_key")
        and c.get("dify_api_base")
    )


def _http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict | None = None,
    timeout: int = 60,
) -> dict:
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {raw[:500]}") from e
    return json.loads(raw) if raw else {}


class _FeishuAes:
    """飞书 Encrypt Key 解密（与开放平台示例一致）。"""

    def __init__(self, key: str) -> None:
        from Crypto.Cipher import AES

        self._AES = AES
        self._key = hashlib.sha256(key.encode("utf-8")).digest()

    def decrypt_string(self, enc_b64: str) -> str:
        from Crypto.Cipher import AES

        enc = base64.b64decode(enc_b64)
        iv = enc[: AES.block_size]
        cipher = AES.new(self._key, AES.MODE_CBC, iv)
        plain = cipher.decrypt(enc[AES.block_size :])
        pad = plain[-1]
        if isinstance(pad, int) and 1 <= pad <= 16:
            plain = plain[:-pad]
        return plain.decode("utf-8")


def _verify_signature(raw_body: bytes, headers: dict[str, str]) -> bool:
    c = _cfg()
    enc_key = c.get("encrypt_key") or ""
    if not enc_key:
        return True
    ts = headers.get("X-Lark-Request-Timestamp", "")
    nonce = headers.get("X-Lark-Request-Nonce", "")
    sig_hdr = headers.get("X-Lark-Signature", "")
    if not ts or not nonce or not sig_hdr:
        return False
    b1 = (ts + nonce + enc_key).encode("utf-8")
    digest = hashlib.sha256(b1 + raw_body).hexdigest()
    return digest == sig_hdr


def _parse_payload(raw_body: bytes, headers: dict[str, str]) -> dict:
    if not _verify_signature(raw_body, headers):
        raise ValueError("飞书签名验证失败")
    outer = json.loads(raw_body.decode("utf-8") or "{}")
    enc_key = (_cfg().get("encrypt_key") or "").strip()
    if outer.get("encrypt") and enc_key:
        inner = _FeishuAes(enc_key).decrypt_string(outer["encrypt"])
        return json.loads(inner)
    return outer


def handle_webhook(raw_body: bytes, headers: dict[str, str]) -> tuple[dict, int]:
    """处理飞书 POST：URL 校验、事件解密、异步调 Dify。"""
    if not is_enabled():
        return {"success": False, "error": "飞书-Dify 未启用或缺少配置"}, 503
    try:
        payload = _parse_payload(raw_body, headers)
    except ValueError as e:
        return {"success": False, "error": str(e)}, 403
    except Exception as e:
        _log.exception("feishu parse")
        return {"success": False, "error": str(e)}, 400

    if payload.get("type") == "url_verification":
        ch = payload.get("challenge", "")
        return {"challenge": ch}, 200

    # 飞书 2.0 事件：schema=2.0；旧版：type=event_callback
    schema = payload.get("schema")
    if schema != "2.0" and payload.get("type") != "event_callback":
        return {"success": True, "ignored": payload.get("type") or schema}, 200

    header = payload.get("header") or {}
    event_id = (header.get("event_id") or "").strip()
    if event_id:
        now = time.time()
        if event_id in _SEEN_EVENTS:
            return {"success": True, "dedup": True}, 200
        _SEEN_EVENTS[event_id] = now
        if len(_SEEN_EVENTS) > _SEEN_MAX:
            cutoff = now - 3600
            for k in list(_SEEN_EVENTS.keys()):
                if _SEEN_EVENTS[k] < cutoff:
                    del _SEEN_EVENTS[k]

    event = payload.get("event") or {}
    if header.get("event_type") != "im.message.receive_v1":
        return {"success": True, "ignored_event": header.get("event_type")}, 200

    threading.Thread(target=_process_message_event, args=(event,), daemon=True).start()
    return {"success": True}, 200


def _tenant_access_token() -> str:
    global _TENANT_TOKEN
    now = time.time()
    if _TENANT_TOKEN.get("token") and (_TENANT_TOKEN.get("expire_at") or 0) > now + 60:
        return _TENANT_TOKEN["token"]
    c = _cfg()
    data = _http_json(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        method="POST",
        body={"app_id": c["app_id"], "app_secret": c["app_secret"]},
        timeout=15,
    )
    if data.get("code") != 0:
        raise RuntimeError(f"飞书 token 失败: {data}")
    _TENANT_TOKEN["token"] = data["tenant_access_token"]
    _TENANT_TOKEN["expire_at"] = now + int(data.get("expire", 7200))
    return _TENANT_TOKEN["token"]


def _send_text(receive_id: str, receive_id_type: str, text: str) -> None:
    token = _tenant_access_token()
    url = (
        "https://open.feishu.cn/open-apis/im/v1/messages"
        f"?receive_id_type={receive_id_type}"
    )
    body = {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": text[:4000]}, ensure_ascii=False),
    }
    data = _http_json(
        url,
        method="POST",
        headers={"Authorization": f"Bearer {token}"},
        body=body,
        timeout=20,
    )
    if data.get("code") != 0:
        raise RuntimeError(f"飞书发消息失败: {data}")


def _ollama_chat(query: str) -> str:
    c = _cfg()
    url = f"{c['ollama_base']}/api/chat"
    data = _http_json(
        url,
        method="POST",
        body={
            "model": c.get("ollama_model") or "qwen2.5:0.5b",
            "messages": [{"role": "user", "content": query}],
            "stream": False,
        },
        timeout=180,
    )
    msg = data.get("message") or {}
    return (msg.get("content") or "").strip() or json.dumps(data, ensure_ascii=False)[:500]


def _dify_chat(query: str, user_key: str) -> str:
    c = _cfg()
    base = (c["dify_api_base"] or "").rstrip("/")
    url = f"{base}/chat-messages"
    conv = _CONV.get(user_key, "")
    body: dict[str, Any] = {
        "inputs": {},
        "query": query,
        "response_mode": "blocking",
        "user": user_key,
    }
    if conv:
        body["conversation_id"] = conv
    try:
        data = _http_json(
            url,
            method="POST",
            headers={"Authorization": f"Bearer {c['dify_api_key']}"},
            body=body,
            timeout=int(c.get("dify_timeout") or "120"),
        )
    except RuntimeError as e:
        err = str(e)
        if c.get("ollama_fallback") or any(
            x in err
            for x in (
                "app_unavailable",
                "502",
                "invalid_param",
                "workflow graph",
                "nodes in workflow",
            )
        ):
            _log.warning("dify failed, ollama fallback: %s", err[:200])
            return _ollama_chat(query)
        raise
    if "conversation_id" in data:
        _CONV[user_key] = data["conversation_id"]
    answer = (data.get("answer") or "").strip()
    if not answer:
        answer = json.dumps(data, ensure_ascii=False)[:500]
    return answer


def _extract_text(message: dict) -> str:
    if message.get("message_type") != "text":
        return ""
    try:
        content = json.loads(message.get("content") or "{}")
    except json.JSONDecodeError:
        return ""
    return (content.get("text") or "").strip()


def _should_reply(message: dict, event: dict) -> bool:
    c = _cfg()
    chat_type = message.get("chat_type") or ""
    if chat_type == "p2p":
        return True
    if c.get("group_reply_all"):
        return True
    bot_oid = (c.get("bot_open_id") or "").strip()
    mentions = message.get("mentions") or []
    if not mentions:
        return False
    for m in mentions:
        mid = (m.get("id") or {}).get("open_id") or ""
        if bot_oid and mid == bot_oid:
            return True
        if not bot_oid:
            return True
    return False


def _process_message_event(event: dict) -> None:
    message = event.get("message") or {}
    sender_info = event.get("sender") or message.get("sender") or {}
    if sender_info.get("sender_type") == "app":
        return
    text = _extract_text(message)
    if not text:
        return
    if not _should_reply(message, event):
        return

    sender = (event.get("sender") or {}).get("sender_id") or {}
    open_id = sender.get("open_id") or "unknown"
    chat_id = message.get("chat_id") or ""
    chat_type = message.get("chat_type") or "p2p"
    user_key = f"feishu-{open_id}"

    try:
        reply = _dify_chat(text, user_key)
    except Exception as e:
        _log.exception("dify chat")
        reply = f"处理失败：{e}"

    try:
        if chat_type == "p2p":
            _send_text(open_id, "open_id", reply)
        else:
            _send_text(chat_id, "chat_id", reply)
    except Exception:
        _log.exception("feishu send")
