# -*- coding: utf-8 -*-
"""3003 与 3001 共用的报价参数、店铺客服配置（MySQL + JSON 备份）。"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from customer_order_store import connect

ROOT = Path(__file__).resolve().parent
QUOTE_DATA_FILE = ROOT / "quote_data.json"


def load_quote_data() -> dict[str, Any] | None:
    try:
        db = connect()
        cur = db.cursor()
        cur.execute("SELECT config_key, config_value FROM quote_config")
        rows = cur.fetchall() or []
        cur.close()
        db.close()
        result: dict[str, Any] = {}
        for r in rows:
            key = r["config_key"]
            val = r["config_value"]
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except json.JSONDecodeError:
                    pass
            result[key] = val
        if result:
            from quote_material_defaults import enrich_quote_data

            return enrich_quote_data(result)
    except Exception as e:
        print(f"[admin_shared_store load_quote_data] MySQL: {e}")
    try:
        with QUOTE_DATA_FILE.open("r", encoding="utf-8") as f:
            from quote_material_defaults import enrich_quote_data

            return enrich_quote_data(json.load(f))
    except Exception:
        return None


def save_quote_data(qd: dict[str, Any] | None) -> bool:
    from quote_material_defaults import enrich_quote_data

    qd = enrich_quote_data(qd or {})
    ok_mysql = False
    try:
        db = connect()
        cur = db.cursor()
        for key, val in qd.items():
            cur.execute(
                "INSERT INTO quote_config (config_key, config_value) VALUES (%s,%s) "
                "ON DUPLICATE KEY UPDATE config_value=VALUES(config_value)",
                (key, json.dumps(val, ensure_ascii=False)),
            )
        db.commit()
        cur.close()
        db.close()
        ok_mysql = True
    except Exception as e:
        print(f"[admin_shared_store save_quote_data] MySQL: {e}")
    ok_file = False
    try:
        with QUOTE_DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(qd, f, ensure_ascii=False, indent=2)
        ok_file = True
    except Exception as e:
        print(f"[admin_shared_store save_quote_data] file: {e}")
    return ok_mysql or ok_file


def load_shop_config() -> list[dict[str, Any]]:
    try:
        db = connect()
        cur = db.cursor()
        cur.execute(
            "SELECT id, shop_name, platform, customer_service, sort_order "
            "FROM shop_config ORDER BY sort_order ASC"
        )
        rows = cur.fetchall() or []
        cur.close()
        db.close()
        if not rows:
            return []
        return [
            {
                "id": r["id"],
                "shop_name": r.get("shop_name") or "",
                "platform": r.get("platform") or "",
                "customer_service": r.get("customer_service") or "",
                "sort_order": r.get("sort_order") or 0,
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[admin_shared_store load_shop_config] {e}")
        return []


def save_shop_config(config: list[dict[str, Any]]) -> bool:
    try:
        db = connect()
        cur = db.cursor()
        cur.execute("TRUNCATE TABLE shop_config")
        for item in config:
            cur.execute(
                "INSERT INTO shop_config (id, shop_name, platform, customer_service, sort_order) "
                "VALUES (%s,%s,%s,%s,%s)",
                (
                    item.get("id", ""),
                    item.get("shop_name", ""),
                    item.get("platform", ""),
                    item.get("customer_service", ""),
                    item.get("sort_order", 0),
                ),
            )
        db.commit()
        cur.close()
        db.close()
        return True
    except Exception as e:
        print(f"[admin_shared_store save_shop_config] {e}")
        return False


def add_shop_item(data: dict[str, Any]) -> dict[str, Any]:
    configs = load_shop_config()
    new_id = f"shop_{len(configs) + 1}_{int(time.time())}"
    new_item = {
        "id": new_id,
        "platform": data.get("platform", "1688"),
        "shop_name": data.get("shop_name", ""),
        "customer_service": data.get("customer_service", ""),
        "sort_order": data.get("sort_order", len(configs) + 1),
    }
    configs.append(new_item)
    if not save_shop_config(configs):
        raise RuntimeError("保存店铺配置失败")
    return new_item


def update_shop_item(config_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    configs = load_shop_config()
    for item in configs:
        if item["id"] == config_id:
            for k in ("platform", "shop_name", "customer_service", "sort_order"):
                if k in patch:
                    item[k] = patch[k]
            if not save_shop_config(configs):
                raise RuntimeError("保存店铺配置失败")
            return item
    return None


def delete_shop_item(config_id: str) -> bool:
    configs = [c for c in load_shop_config() if c.get("id") != config_id]
    return save_shop_config(configs)
