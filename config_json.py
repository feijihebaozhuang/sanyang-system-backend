# -*- coding: utf-8 -*-
"""
Admin 业务配置（JSON）工具。

铁律：配置在 JSON、逻辑在 .py；部署只推 .py，永不覆盖服务器上 admin 改好的 JSON。
- 启动时仅「缺键补默认」，不覆盖已有键值。
- 仅 Admin 保存 API 可写 JSON；业务代码只读。
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent

# permission_data 中由 data.json 托管的键（admin 页面可改）
PERMISSION_JSON_KEYS = frozenset(
    {
        "processes",
        "positions",
        "employees",
        "production_material_mapping",
        "permissions",
        "employee_enabled",
        "process_timeouts",
    }
)


def data_json_path(base_dir: str | Path | None = None) -> Path:
    root = Path(base_dir) if base_dir else _ROOT
    return root / "data.json"


def quote_json_path(base_dir: str | Path | None = None) -> Path:
    root = Path(base_dir) if base_dir else _ROOT
    return root / "quote_data.json"


def shop_config_json_path(base_dir: str | Path | None = None) -> Path:
    root = Path(base_dir) if base_dir else _ROOT
    return root / "shop_config.json"


def merge_missing_keys(target: dict, defaults: dict) -> None:
    """仅补齐 target 中不存在的键（递归 dict），永不覆盖已有值。"""
    for key, default_val in defaults.items():
        if key not in target:
            target[key] = copy.deepcopy(default_val)
        elif isinstance(default_val, dict) and isinstance(target.get(key), dict):
            merge_missing_keys(target[key], default_val)


def read_json_file(path: str | Path, default: Any) -> Any:
    p = Path(path)
    if not p.is_file():
        return copy.deepcopy(default)
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[config_json] 读取失败 {p}: {e}")
        return copy.deepcopy(default)
    if isinstance(default, dict) and isinstance(data, dict):
        merge_missing_keys(data, default)
        return data
    return data


def read_permission_overlay(base_dir: str | Path | None = None) -> dict[str, Any]:
    """从 data.json 读取 permission_data 片段（只读）。"""
    raw = read_json_file(data_json_path(base_dir), {})
    pd = raw.get("permission_data")
    return pd if isinstance(pd, dict) else {}


def apply_permission_overlay(
    permission_data: dict,
    overlay: dict[str, Any] | None = None,
    *,
    keys: frozenset[str] = PERMISSION_JSON_KEYS,
) -> None:
    """用 JSON 中的配置覆盖内存（仅当 JSON 里该键有内容）。"""
    overlay = overlay if overlay is not None else read_permission_overlay()
    for key in keys:
        val = overlay.get(key)
        if val is None:
            continue
        if isinstance(val, list) and not val:
            continue
        if isinstance(val, dict) and not val:
            continue
        permission_data[key] = copy.deepcopy(val)


def write_permission_overlay(
    permission_data: dict,
    *,
    base_dir: str | Path | None = None,
    keys: frozenset[str] = PERMISSION_JSON_KEYS,
) -> bool:
    """Admin 保存：合并写入 data.json（保留 JSON 中其它顶层字段）。"""
    path = data_json_path(base_dir)
    existing: dict[str, Any] = {}
    if path.is_file():
        try:
            with path.open("r", encoding="utf-8") as f:
                existing = json.load(f)
        except (OSError, json.JSONDecodeError):
            existing = {}
    if not isinstance(existing, dict):
        existing = {}
    pd = existing.setdefault("permission_data", {})
    if not isinstance(pd, dict):
        pd = {}
        existing["permission_data"] = pd
    for key in keys:
        if key in permission_data:
            pd[key] = copy.deepcopy(permission_data[key])
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        print(f"[config_json] 写入失败 {path}: {e}")
        return False


def match_material_from_mapping(text: str, mapping: list[dict] | None) -> str:
    """按 data.json 中 production_material_mapping 匹配材质。"""
    low = (text or "").lower()
    if not mapping:
        return ""
    best = ""
    best_len = 0
    for row in mapping:
        if not isinstance(row, dict):
            continue
        label = (row.get("label") or "").strip()
        kws = (row.get("keywords") or "").strip()
        for kw in (k.strip() for k in kws.split(",") if k.strip()):
            kl = kw.lower()
            if kl and kl in low and len(kw) > best_len:
                best = label
                best_len = len(kw)
    return best
