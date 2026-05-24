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
        "role_permissions",
        "employee_roles",
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


def _overlay_value_usable(val: Any) -> bool:
    """vault/JSON 覆盖时：空列表、空 dict 视为无效，避免冲掉 admin 已配好的工序等。"""
    if val is None:
        return False
    if isinstance(val, (list, dict, str)) and not val:
        return False
    return True


def _apply_vault_keys(permission_data: dict, remote: dict[str, Any], *, keys: frozenset[str]) -> None:
    """从 vault 合并：仅非空键覆盖，永不把工序/映射等清空。"""
    for key in keys:
        val = remote.get(key)
        if not _overlay_value_usable(val):
            continue
        permission_data[key] = copy.deepcopy(val)


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
    """读取 permission_data：优先独立配置服务器，否则 data.json。"""
    try:
        import permission_vault as pv

        if pv.vault_enabled():
            try:
                remote = pv.fetch_permission_overlay()
                if remote:
                    return remote
            except Exception as e:
                print(f"[config_json] 保险库拉取失败，回退 data.json: {e}")
    except ImportError:
        pass
    raw = read_json_file(data_json_path(base_dir), {})
    pd = raw.get("permission_data")
    return pd if isinstance(pd, dict) else {}


def apply_permission_overlay(
    permission_data: dict,
    overlay: dict[str, Any] | None = None,
    *,
    keys: frozenset[str] = PERMISSION_JSON_KEYS,
) -> None:
    """用 JSON/保险库配置补齐内存：仅非空键补入，永不因 vault 空数据冲掉已有工序。"""
    overlay = overlay if overlay is not None else read_permission_overlay()
    for key in keys:
        val = overlay.get(key)
        if val is None:
            continue
        if isinstance(val, list) and not val:
            continue
        if isinstance(val, dict) and not val:
            continue
        if key == "permissions" and isinstance(val, dict):
            target = permission_data.setdefault("permissions", {})
            for emp, feats in val.items():
                if not isinstance(feats, dict):
                    continue
                if emp not in target:
                    target[emp] = copy.deepcopy(feats)
                else:
                    for feat, enabled in feats.items():
                        if feat not in target[emp]:
                            target[emp][feat] = enabled
            continue
        if key == "employee_enabled" and isinstance(val, dict):
            target = permission_data.setdefault("employee_enabled", {})
            for emp, enabled in val.items():
                if emp not in target:
                    target[emp] = enabled
            continue
        if key == "role_permissions" and isinstance(val, dict):
            target = permission_data.setdefault("role_permissions", {})
            for role, feats in val.items():
                if not isinstance(feats, dict):
                    continue
                if role not in target:
                    target[role] = copy.deepcopy(feats)
                else:
                    for feat, enabled in feats.items():
                        if feat not in target[role]:
                            target[role][feat] = enabled
            continue
        if key == "employee_roles" and isinstance(val, dict):
            target = permission_data.setdefault("employee_roles", {})
            for emp, role in val.items():
                if emp not in target:
                    target[emp] = role
            continue
        if isinstance(val, dict):
            if key not in permission_data or not isinstance(permission_data.get(key), dict):
                permission_data[key] = copy.deepcopy(val)
            else:
                merge_missing_keys(permission_data[key], val)
            continue
        if isinstance(val, list):
            if key not in permission_data or not permission_data[key]:
                permission_data[key] = copy.deepcopy(val)
            continue
        if key not in permission_data:
            permission_data[key] = copy.deepcopy(val)


def refresh_permission_from_vault(permission_data: dict) -> None:
    """读接口刷新：多 worker 下从保险库拉最新 permission_data（即时生效）。"""
    try:
        import permission_vault as pv

        if not pv.vault_enabled():
            return
        remote = pv.fetch_permission_overlay()
        if not remote:
            return
        _apply_vault_keys(permission_data, remote, keys=PERMISSION_JSON_KEYS)
    except Exception as e:
        print(f"[config_json] 保险库刷新失败: {e}")


def _write_permission_data_local(
    permission_data: dict,
    *,
    base_dir: str | Path | None = None,
    keys: frozenset[str] = PERMISSION_JSON_KEYS,
) -> bool:
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


def write_permission_overlay(
    permission_data: dict,
    *,
    base_dir: str | Path | None = None,
    keys: frozenset[str] = PERMISSION_JSON_KEYS,
) -> bool:
    """Admin 保存：先写本机 data.json，再尽力 POST 156 vault。"""
    local_ok = _write_permission_data_local(
        permission_data, base_dir=base_dir, keys=keys
    )
    if not local_ok:
        return False
    try:
        import permission_vault as pv

        if pv.vault_enabled() and not pv.vault_readonly_on_app():
            if not pv.push_permission_overlay(permission_data, keys=keys):
                print("[config_json] vault POST 失败，已保留本机 data.json 镜像")
    except ImportError:
        pass
    return True


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
        label = (row.get("label") or row.get("material_name") or "").strip()
        kws = (row.get("keywords") or "").strip()
        for kw in (k.strip() for k in kws.split(",") if k.strip()):
            kl = kw.lower()
            if kl and kl in low and len(kw) > best_len:
                best = label
                best_len = len(kw)
    return best
