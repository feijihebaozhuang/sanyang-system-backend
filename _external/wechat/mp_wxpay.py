# -*- coding: utf-8 -*-
"""微信小程序 JSAPI 支付（微信支付 API v3）。"""
from __future__ import annotations

import base64
import json
import os
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_ROOT = Path(__file__).resolve().parent


def _mch_id() -> str:
    return (os.getenv("WX_PAY_MCH_ID") or os.getenv("WXPAY_MCH_ID") or "").strip()


def _app_id() -> str:
    return (os.getenv("WX_MP_APPID") or "").strip()


def _api_v3_key() -> str:
    return (os.getenv("WX_PAY_API_V3_KEY") or os.getenv("WXPAY_API_V3_KEY") or "").strip()


def _cert_serial() -> str:
    return (os.getenv("WX_PAY_CERT_SERIAL") or os.getenv("WXPAY_SERIAL_NO") or "").strip()


def _notify_url() -> str:
    return (os.getenv("WX_PAY_NOTIFY_URL") or "https://feijihe.top/api/mp/pay/notify").strip()


def wxpay_configured() -> bool:
    return bool(_mch_id() and _app_id() and _api_v3_key() and _cert_serial() and _load_private_key())


def _private_key_path() -> Path:
    p = (os.getenv("WX_PAY_PRIVATE_KEY_FILE") or "wx_pay_apiclient_key.pem").strip()
    path = Path(p)
    if not path.is_absolute():
        path = _ROOT / path
    return path


def _load_private_key():
    pem_inline = (os.getenv("WX_PAY_PRIVATE_KEY") or "").strip()
    if pem_inline:
        pem = pem_inline.replace("\\n", "\n")
    else:
        path = _private_key_path()
        if not path.is_file():
            return None
        pem = path.read_text(encoding="utf-8")
    try:
        return serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
    except Exception:
        return None


def _sign_message(message: str) -> str:
    key = _load_private_key()
    if not key:
        raise RuntimeError("未配置微信支付商户私钥")
    sig = key.sign(message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode("ascii")


def _auth_header(method: str, url_path: str, body: str) -> str:
    ts = str(int(time.time()))
    nonce = secrets.token_hex(16)
    message = f"{method}\n{url_path}\n{ts}\n{nonce}\n{body}\n"
    sign = _sign_message(message)
    return (
        f'WECHATPAY2-SHA256-RSA2048 mchid="{_mch_id()}",'
        f'nonce_str="{nonce}",signature="{sign}",timestamp="{ts}",serial_no="{_cert_serial()}"'
    )


def _post_v3(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    req = urllib.request.Request(
        f"https://api.mch.weixin.qq.com{path}",
        data=body.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": _auth_header("POST", path, body),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"message": raw[:500]}
        return {"success": False, "http_status": e.code, **data}


def create_jsapi_prepay(
    *,
    openid: str,
    out_trade_no: str,
    description: str,
    total_fen: int,
    notify_url: str | None = None,
) -> dict[str, Any]:
    if not wxpay_configured():
        return {"success": False, "error": "微信支付未配置（商户号/证书/APIv3密钥）"}
    total_fen = int(total_fen)
    if total_fen < 1:
        return {"success": False, "error": "支付金额无效"}
    out_trade_no = (out_trade_no or "").strip()[:32]
    if len(out_trade_no) < 6:
        return {"success": False, "error": "商户订单号无效"}

    payload = {
        "appid": _app_id(),
        "mchid": _mch_id(),
        "description": (description or "三羊包装订单")[:127],
        "out_trade_no": out_trade_no,
        "notify_url": notify_url or _notify_url(),
        "amount": {"total": total_fen, "currency": "CNY"},
        "payer": {"openid": openid},
    }
    res = _post_v3("/v3/pay/transactions/jsapi", payload)
    if res.get("prepay_id"):
        return {"success": True, "prepay_id": res["prepay_id"], "raw": res}
    err = res.get("message") or res.get("code") or json.dumps(res, ensure_ascii=False)[:300]
    return {"success": False, "error": str(err), "raw": res}


def build_miniprogram_pay_params(prepay_id: str) -> dict[str, str]:
    ts = str(int(time.time()))
    nonce = secrets.token_hex(16)
    package = f"prepay_id={prepay_id}"
    message = f"{_app_id()}\n{ts}\n{nonce}\n{package}\n"
    pay_sign = _sign_message(message)
    return {
        "timeStamp": ts,
        "nonceStr": nonce,
        "package": package,
        "signType": "RSA",
        "paySign": pay_sign,
    }


def decrypt_notify_resource(resource: dict[str, Any]) -> dict[str, Any]:
    key = _api_v3_key().encode("utf-8")
    nonce = (resource.get("nonce") or "").encode("utf-8")
    ciphertext = base64.b64decode(resource.get("ciphertext") or "")
    associated = (resource.get("associated_data") or "").encode("utf-8")
    plain = AESGCM(key).decrypt(nonce, ciphertext, associated)
    return json.loads(plain.decode("utf-8"))


def parse_pay_notify(body: dict[str, Any]) -> dict[str, Any]:
    if not body:
        return {"success": False, "error": "empty body"}
    resource = body.get("resource")
    if not isinstance(resource, dict):
        return {"success": False, "error": "无 resource"}
    try:
        data = decrypt_notify_resource(resource)
    except Exception as ex:
        return {"success": False, "error": f"解密失败: {ex}"}
    if (data.get("trade_state") or "") != "SUCCESS":
        return {"success": False, "error": "非 SUCCESS", "data": data}
    return {
        "success": True,
        "out_trade_no": (data.get("out_trade_no") or "").strip(),
        "transaction_id": (data.get("transaction_id") or "").strip(),
        "amount_total": int((data.get("amount") or {}).get("total") or 0),
        "payer_openid": ((data.get("payer") or {}).get("openid") or "").strip(),
        "data": data,
    }
