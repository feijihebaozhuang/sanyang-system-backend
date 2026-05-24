# -*- coding: utf-8 -*-
"""从环境变量 / .env 加载敏感配置。请在项目根目录配置 .env（勿提交仓库）。"""
from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore

_ROOT = Path(__file__).resolve().parent


def _ensure_dotenv() -> None:
    if not load_dotenv:
        return
    env_path = _ROOT / ".env"
    load_dotenv(env_path, override=False)


_ensure_dotenv()


def _require(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(
            f"缺少必填环境变量 {name}。请复制 .env.example 为 .env 并填写，见项目根目录。"
        )
    return v


def get_db_config() -> dict:
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1").strip(),
        "port": int(os.getenv("MYSQL_PORT", "3306") or "3306"),
        "user": os.getenv("MYSQL_USER", "root").strip(),
        "password": _require("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE", "sanyang").strip(),
        "charset": "utf8mb4",
        "autocommit": True,
    }


def get_flask_secret_key() -> str:
    # 与历史硬编码一致，避免升级后 .env 未配时全员刷新掉登录
    legacy = "feijihe_sanyang_2026_secret_key_!@#"
    return os.getenv("FLASK_SECRET_KEY", "").strip() or legacy


def get_jst_config() -> dict:
    app_key = os.getenv("JST_APP_KEY", "").strip()
    return {
        "app_key": app_key,
        "app_secret": os.getenv("JST_APP_SECRET", "").strip(),
        "api_url": os.getenv(
            "JST_API_URL", "https://open.erp321.com/api/open/query.aspx"
        ).strip(),
        "partnerid": os.getenv("JST_PARTNER_ID", app_key).strip(),
    }


def get_wechat_token() -> str:
    return os.getenv("WECHAT_TOKEN", "").strip()


def get_feishu_dify_config() -> dict:
    """飞书机器人 ↔ Dify 应用 API（见 docs/FEISHU_DIFY.md）。"""
    enabled = os.getenv("FEISHU_DIFY_ENABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    return {
        "enabled": enabled,
        "app_id": os.getenv("FEISHU_APP_ID", "").strip(),
        "app_secret": os.getenv("FEISHU_APP_SECRET", "").strip(),
        "verification_token": os.getenv("FEISHU_VERIFICATION_TOKEN", "").strip(),
        "encrypt_key": os.getenv("FEISHU_ENCRYPT_KEY", "").strip(),
        "bot_open_id": os.getenv("FEISHU_BOT_OPEN_ID", "").strip(),
        "group_reply_all": os.getenv("FEISHU_GROUP_REPLY_ALL", "").strip().lower()
        in ("1", "true", "yes"),
        "dify_api_base": os.getenv(
            "DIFY_API_BASE", "https://api.dify.ai/v1"
        ).strip().rstrip("/"),
        "dify_api_key": os.getenv("DIFY_API_KEY", "").strip(),
        "dify_timeout": os.getenv("DIFY_TIMEOUT", "120").strip() or "120",
        "ollama_base": os.getenv("OLLAMA_BASE", "http://127.0.0.1:11434").strip().rstrip(
            "/"
        ),
        "ollama_model": os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b").strip() or "qwen2.5:0.5b",
        "ollama_fallback": os.getenv("FEISHU_USE_OLLAMA_FALLBACK", "").strip().lower()
        in ("1", "true", "yes", "on"),
    }


def get_km_config() -> dict:
    return {
        "app_key": os.getenv("KM_APP_KEY", "").strip(),
        "app_secret": os.getenv("KM_APP_SECRET", "").strip(),
        "session": os.getenv("KM_SESSION", "").strip(),
        "api_url": os.getenv("KM_API_URL", "https://gw.superboss.cc/router").strip(),
        "token_file": os.getenv("KM_TOKEN_FILE", str(_ROOT / "km_token.json")).strip(),
    }


def get_alibaba_api_defaults() -> dict:
    key_s = os.getenv("ALIBABA_APP_KEY", "").strip()
    app_key = int(key_s) if key_s.isdigit() else 0
    return {
        "app_key": app_key,
        "app_secret": os.getenv("ALIBABA_APP_SECRET", "").strip(),
        "server": os.getenv("ALIBABA_SERVER", "gw.open.1688.com").strip()
        or "gw.open.1688.com",
    }


def _raw_alibaba_shops_list() -> list:
    fp = os.getenv("ALIBABA_SHOPS_FILE", "").strip()
    if fp:
        p = Path(fp)
        if not p.is_file():
            raise RuntimeError(f"环境变量 ALIBABA_SHOPS_FILE 指向的文件不存在: {fp}")
        raw = p.read_text(encoding="utf-8")
    else:
        raw = os.getenv("ALIBABA_SHOPS_JSON", "").strip()
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise RuntimeError("ALIBABA_SHOPS_JSON / 店铺配置文件顶层必须是 JSON 数组")
    return data


def get_alibaba_shops() -> list:
    defaults = get_alibaba_api_defaults()
    out: list = []
    for s in _raw_alibaba_shops_list():
        if not isinstance(s, dict):
            continue
        name = (s.get("shop_name") or "").strip()
        token = (s.get("access_token") or "").strip()
        if not name or not token:
            continue
        ak = s.get("app_key", defaults["app_key"])
        if isinstance(ak, str) and ak.strip().isdigit():
            ak = int(ak.strip())
        elif isinstance(ak, (int, float)):
            ak = int(ak)
        else:
            ak = defaults["app_key"]
        sec = (s.get("app_secret") or defaults["app_secret"] or "").strip()
        srv = (s.get("server") or defaults["server"] or "gw.open.1688.com").strip()
        if not ak:
            ak = defaults["app_key"]
        if not sec:
            sec = defaults["app_secret"]
        if not ak or not sec:
            continue
        out.append(
            {
                "shop_name": name,
                "app_key": ak,
                "app_secret": sec,
                "access_token": token,
                "server": srv,
            }
        )
    return out


def get_alibaba_default_app_config() -> dict:
    d = get_alibaba_api_defaults()
    token = os.getenv("ALIBABA_DEFAULT_ACCESS_TOKEN", "").strip()
    shops = get_alibaba_shops()
    if not token and shops:
        token = shops[0]["access_token"]
    if not d["app_key"] and shops:
        d = {
            "app_key": shops[0]["app_key"],
            "app_secret": shops[0]["app_secret"],
            "server": shops[0]["server"],
        }
    return {
        "app_key": d["app_key"],
        "app_secret": d["app_secret"],
        "access_token": token,
        "server": d["server"],
    }


DB_CONFIG = get_db_config()
FLASK_SECRET_KEY = get_flask_secret_key()
JST_CONFIG = get_jst_config()
ALIBABA_CONFIG = get_alibaba_default_app_config()
ALIBABA_SHOPS = get_alibaba_shops()

# 报价前端读取的大 JSON（与 MySQL quote_config 并存）
QUOTE_DATA_FILE = str(_ROOT / "quote_data.json")
