# -*- coding: utf-8 -*-
"""订单加急等 order_extra：MySQL order_extras 为权威源（客服端/生产端共享）。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable


def load_urgent_map(get_db_fn: Callable) -> dict[str, bool]:
    out: dict[str, bool] = {}
    try:
        db = get_db_fn()
        cur = db.cursor()
        cur.execute("SELECT so_id, urgent FROM order_extras")
        for row in cur.fetchall():
            if not isinstance(row, dict):
                continue
            sid = str(row.get("so_id") or "").strip()
            if sid:
                out[sid] = bool(row.get("urgent"))
        cur.close()
        db.close()
    except Exception as e:
        print(f"[order_extra_store] 读取 order_extras 失败: {e}")
    return out


def merge_urgent_into(order_extra: dict, get_db_fn: Callable) -> None:
    """把 MySQL 加急状态合并进内存 order_extra（不删 remark 等其它键）。"""
    for so_id, urgent in load_urgent_map(get_db_fn).items():
        entry = order_extra.setdefault(so_id, {})
        if not isinstance(entry, dict):
            order_extra[so_id] = {"urgent": urgent}
        else:
            entry["urgent"] = urgent


def upsert_urgent(get_db_fn: Callable, so_id: str, urgent: bool) -> bool:
    oid = (so_id or "").strip()
    if not oid:
        return False
    try:
        db = get_db_fn()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO order_extras (so_id, urgent) VALUES (%s,%s) "
            "ON DUPLICATE KEY UPDATE urgent=VALUES(urgent)",
            (oid, 1 if urgent else 0),
        )
        db.commit()
        cur.close()
        db.close()
        return True
    except Exception as e:
        print(f"[order_extra_store] 写入加急失败 {oid}: {e}")
        return False


def mirror_order_extra_to_data_json(
    order_extra: dict,
    *,
    data_json: str | Path | None = None,
) -> bool:
    """镜像 order_extra 到 stable/data.json，供生产端进程兜底读取。"""
    root = Path(__file__).resolve().parent
    path = Path(data_json) if data_json else root / "data.json"
    existing: dict[str, Any] = {}
    if path.is_file():
        try:
            with path.open("r", encoding="utf-8") as f:
                existing = json.load(f)
        except (OSError, json.JSONDecodeError):
            existing = {}
    if not isinstance(existing, dict):
        existing = {}
    existing["order_extra"] = dict(order_extra)
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        print(f"[order_extra_store] 镜像 data.json 失败: {e}")
        return False
