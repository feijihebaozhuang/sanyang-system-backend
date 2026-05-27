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


def write_quote_json_partial(
    updates: dict[str, Any],
    *,
    base_dir: str | Path | None = None,
) -> bool:
    """只更新 quote_data.json 中的若干键（不覆盖整文件其它字段）。"""
    if not isinstance(updates, dict) or not updates:
        return False
    path = quote_json_path(base_dir)
    existing = read_json_file(path, {})
    if not isinstance(existing, dict):
        existing = {}
    for key, val in updates.items():
        existing[key] = copy.deepcopy(val)
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        print(f"[config_json] write_quote_json_partial 失败 {path}: {e}")
        return False


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


def _read_local_permission_slice(base_dir: str | Path | None = None) -> dict[str, Any]:
    raw = read_json_file(data_json_path(base_dir), {})
    pd = raw.get("permission_data") if isinstance(raw, dict) else None
    return pd if isinstance(pd, dict) else {}


def read_permission_overlay(base_dir: str | Path | None = None) -> dict[str, Any]:
    """
    读取 permission_data 权威视图（按键合并）：
    - 本机 stable/data.json 中**非空键优先**（admin 网页保存写这里，Gunicorn 多 worker 读盘即同步）
    - vault 仅补齐本机缺失/为空的键（156 备份、新机 bootstrap）
    """
    local = _read_local_permission_slice(base_dir)
    remote: dict[str, Any] = {}
    try:
        import permission_vault as pv

        if pv.vault_enabled():
            try:
                remote = pv.fetch_permission_overlay()
            except Exception as e:
                print(f"[config_json] 保险库拉取失败，仅用本机 data.json: {e}")
                remote = {}
            if not isinstance(remote, dict):
                remote = {}
    except ImportError:
        pass
    out: dict[str, Any] = {}
    for key in PERMISSION_JSON_KEYS:
        lv = local.get(key)
        rv = remote.get(key) if remote else None
        if _overlay_value_usable(lv):
            out[key] = copy.deepcopy(lv)
        elif _overlay_value_usable(rv):
            out[key] = copy.deepcopy(rv)
    return out


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


def reload_permission_memory(
    permission_data: dict,
    *,
    base_dir: str | Path | None = None,
    from_vault: bool = False,
) -> dict[str, Any]:
    """
    刷新内存中的 permission_data。
    - 默认只读本机 stable/data.json（多 worker 同步、admin 刚保存的内容）
    - from_vault=True 时才合并 156（仅启动/bootstrap 用，避免 vault 旧数据冲掉本机）
    """
    if from_vault:
        overlay = read_permission_overlay(base_dir)
    else:
        overlay = _read_local_permission_slice(base_dir)
    for key in PERMISSION_JSON_KEYS:
        val = overlay.get(key)
        if _overlay_value_usable(val):
            permission_data[key] = copy.deepcopy(val)
    meta: dict[str, Any] = {"reloaded": True, "source": "vault" if from_vault else "local"}
    try:
        import permission_vault as pv

        meta["vault_enabled"] = pv.vault_enabled()
        meta["vault_readonly"] = pv.vault_readonly_on_app()
    except ImportError:
        meta["vault_enabled"] = False
        meta["vault_readonly"] = False
    return meta


def refresh_permission_from_vault(permission_data: dict) -> None:
    """兼容旧名：读接口刷新（多 worker 下必须用 reload_permission_memory）。"""
    reload_permission_memory(permission_data)


def write_data_json_partial(
    updates: dict[str, Any],
    *,
    base_dir: str | Path | None = None,
) -> bool:
    """写入 data.json 顶层键（如 employees_master、resigned_employees），不覆盖其它键。"""
    if not updates:
        return True
    path = data_json_path(base_dir)
    existing: dict[str, Any] = read_json_file(path, {})
    if not isinstance(existing, dict):
        existing = {}
    for key, val in updates.items():
        existing[key] = copy.deepcopy(val)
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        print(f"[config_json] write_data_json_partial 失败 {path}: {e}")
        return False


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
    """Admin 保存：写本机 data.json，并尽力 POST 156 vault。返回是否整体成功。"""
    result = write_permission_overlay_detail(
        permission_data, base_dir=base_dir, keys=keys
    )
    return bool(result.get("ok"))


def write_permission_overlay_detail(
    permission_data: dict,
    *,
    base_dir: str | Path | None = None,
    keys: frozenset[str] = PERMISSION_JSON_KEYS,
) -> dict[str, Any]:
    """返回 local_ok / vault_ok / 错误说明，供 API 提示 admin。"""
    local_ok = _write_permission_data_local(
        permission_data, base_dir=base_dir, keys=keys
    )
    vault_ok: bool | None = None
    vault_error = ""
    if not local_ok:
        return {
            "ok": False,
            "local_ok": False,
            "vault_ok": None,
            "vault_error": "写入 stable/data.json 失败，请检查目录权限",
        }
    try:
        import permission_vault as pv

        if pv.vault_enabled():
            if pv.vault_readonly_on_app():
                vault_ok = False
                vault_error = (
                    "已保存本机 data.json；未配置 PERMISSION_VAULT_WRITE_URL，"
                    "156 权限机未更新。请在 87 stable/.env 配置 WRITE_URL 后重启。"
                )
            elif not pv.push_permission_overlay(permission_data, keys=keys):
                vault_ok = False
                vault_error = "本机已保存，但 POST 156 权限机失败，请检查 TOKEN/防火墙"
            else:
                vault_ok = True
    except ImportError:
        pass
    except Exception as exc:
        vault_ok = False
        vault_error = f"vault 异常: {exc}"
        import traceback

        traceback.print_exc()
    # 本机 data.json 成功即视为保存成功；vault 失败仅警告（避免刷新后像没保存）
    return {
        "ok": bool(local_ok),
        "local_ok": local_ok,
        "vault_ok": vault_ok,
        "vault_error": vault_error,
    }


def quote_rows_to_production_mapping(rows: list[dict] | None) -> list[dict]:
    """报价页 material_mapping → permission_data.production_material_mapping。"""
    out: list[dict] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = (row.get("material_name") or row.get("label") or "").strip()
        keywords = (row.get("keywords") or "").strip()
        if label or keywords:
            out.append({"label": label, "keywords": keywords})
    return out


def sync_production_mapping_from_quote(
    permission_data: dict,
    quote_rows: list[dict] | None,
    *,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    """保存报价材料映射时同步写入 permission_data + 本机 JSON + 156。"""
    mapping = quote_rows_to_production_mapping(quote_rows)
    permission_data["production_material_mapping"] = mapping
    return write_permission_overlay_detail(
        permission_data, base_dir=base_dir, keys=frozenset({"production_material_mapping"})
    )
