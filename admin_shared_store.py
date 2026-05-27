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


def _load_quote_json_raw() -> dict[str, Any]:
    try:
        with QUOTE_DATA_FILE.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _parse_quote_config_value(val: Any) -> Any:
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            pass
    return val


def _load_material_mapping_raw() -> list[dict[str, Any]]:
    """读取 material_mapping 原样：MySQL quote_config 优先，无则 quote_data.json。"""
    try:
        db = connect()
        cur = db.cursor()
        cur.execute(
            "SELECT config_value FROM quote_config WHERE config_key=%s LIMIT 1",
            ("material_mapping",),
        )
        row = cur.fetchone()
        cur.close()
        db.close()
        if row:
            val = _parse_quote_config_value(row.get("config_value"))
            if isinstance(val, list):
                return val
    except Exception as e:
        print(f"[admin_shared_store material_mapping MySQL] {e}")

    file_raw = _load_quote_json_raw()
    mm = file_raw.get("material_mapping")
    return list(mm) if isinstance(mm, list) else []


def load_quote_data() -> dict[str, Any] | None:
    mysql_result: dict[str, Any] | None = None
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
            result[key] = _parse_quote_config_value(r["config_value"])
        if result:
            mysql_result = result
    except Exception as e:
        print(f"[admin_shared_store load_quote_data] MySQL: {e}")

    file_raw = _load_quote_json_raw()
    if mysql_result and file_raw:
        merged = dict(mysql_result)
        mysql_mm = mysql_result.get("material_mapping")
        if not isinstance(mysql_mm, list) or not mysql_mm:
            file_mm = file_raw.get("material_mapping")
            if isinstance(file_mm, list):
                merged["material_mapping"] = file_mm
        from quote_material_defaults import enrich_quote_data

        # admin 读配置：不合并默认关键词，避免页面/保存前把用户改短的词又扩回去
        return enrich_quote_data(merged, merge_defaults=False)
    if mysql_result:
        from quote_material_defaults import enrich_quote_data

        return enrich_quote_data(mysql_result, merge_defaults=False)
    if file_raw:
        from quote_material_defaults import enrich_quote_data

        return enrich_quote_data(file_raw, merge_defaults=False)
    return None


def load_material_mapping_admin() -> list[dict[str, Any]]:
    """3003 材料映射页：MySQL 优先，不合并默认关键词。"""
    from quote_material_defaults import enrich_material_mapping

    return enrich_material_mapping(_load_material_mapping_raw(), merge_defaults=False)


def save_quote_mapping(rows: list[dict[str, Any]]) -> tuple[bool, str, list[dict[str, Any]]]:
    """仅保存 material_mapping（MySQL 单键 + quote_data.json 局部）。admin 保存不追加默认关键词。"""
    from quote_material_defaults import enrich_material_mapping

    rows = enrich_material_mapping(rows if isinstance(rows, list) else [], merge_defaults=False)
    err_parts: list[str] = []
    ok_mysql = False
    try:
        db = connect()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO quote_config (config_key, config_value) VALUES (%s,%s) "
            "ON DUPLICATE KEY UPDATE config_value=VALUES(config_value)",
            ("material_mapping", json.dumps(rows, ensure_ascii=False)),
        )
        db.commit()
        cur.close()
        db.close()
        ok_mysql = True
    except Exception as e:
        err_parts.append(f"MySQL: {e}")
    import config_json

    ok_json = config_json.write_quote_json_partial({"material_mapping": rows})
    if not ok_json:
        err_parts.append("quote_data.json 写入失败")
    if ok_mysql or ok_json:
        return True, "", rows
    return False, "; ".join(err_parts) or "保存失败", rows


def save_quote_data(qd: dict[str, Any] | None) -> bool:
    from quote_material_defaults import enrich_quote_data

    # 保存时禁止把默认词合并进 keywords（否则改报价单价会把材料映射冲掉）
    qd = enrich_quote_data(qd or {}, merge_defaults=False)
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
