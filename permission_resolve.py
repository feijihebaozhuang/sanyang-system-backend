# -*- coding: utf-8 -*-
"""员工权限解析：兼容 admin 空 employee_name、MySQL employee_permissions。"""
from __future__ import annotations

from typing import Any, Callable

_PERM_LEGACY_KEY = "聚水潭"
_PERM_CURRENT_KEY = "快麦ERP"


def migrate_perm_dict(perms: dict | None) -> dict:
    if not isinstance(perms, dict):
        return perms or {}
    if _PERM_LEGACY_KEY in perms and _PERM_CURRENT_KEY not in perms:
        perms[_PERM_CURRENT_KEY] = perms.pop(_PERM_LEGACY_KEY)
    elif _PERM_LEGACY_KEY in perms:
        perms.pop(_PERM_LEGACY_KEY, None)
    return perms


def merge_employee_permissions_from_db(
    permission_data: dict,
    get_db_fn: Callable[[], Any],
) -> None:
    try:
        db = get_db_fn()
        cur = db.cursor()
        cur.execute(
            "SELECT employee_name, permission_key, enabled FROM employee_permissions"
        )
        rows = cur.fetchall() or []
        cur.close()
        db.close()
    except Exception:
        return
    base = permission_data.setdefault("permissions", {})
    for r in rows:
        if isinstance(r, dict):
            en = (r.get("employee_name") or "").strip()
            pk = (r.get("permission_key") or "").strip()
            val = bool(r.get("enabled"))
        else:
            en = (r[0] or "").strip()
            pk = (r[1] or "").strip()
            val = bool(r[2])
        if not en or not pk:
            continue
        if pk == _PERM_LEGACY_KEY:
            pk = _PERM_CURRENT_KEY
        if en not in base:
            base[en] = {}
        if pk not in base[en]:
            base[en][pk] = val
    permission_data["permissions"] = base


_SUPER_ADMIN_USERNAMES = frozenset({"admin", "daiyali"})
_SUPER_ADMIN_EMPLOYEE_NAMES = frozenset({"戴雅利"})


def is_super_admin_account(username: str, user: dict | None) -> bool:
    u = user or {}
    un = (username or "").strip().lower()
    if u.get("is_system"):
        return True
    if un in _SUPER_ADMIN_USERNAMES:
        return True
    if (u.get("role") or "").strip() == "超级管理员":
        return True
    en = (u.get("employee_name") or "").strip()
    if en in _SUPER_ADMIN_EMPLOYEE_NAMES and un in _SUPER_ADMIN_USERNAMES:
        return True
    if en in _SUPER_ADMIN_EMPLOYEE_NAMES and (u.get("name") or "").strip() in _SUPER_ADMIN_EMPLOYEE_NAMES:
        return True
    return False


def normalize_user_record(username: str, user: dict | None) -> dict:
    """保证 admin / 戴雅利 系统账号永不被 employee_roles 同步降为普通员工。"""
    u = dict(user or {})
    un = (username or "").strip()
    if is_super_admin_account(un, u):
        if un == "admin" or u.get("is_system"):
            u["is_system"] = True
        u["role"] = "超级管理员"
        if un == "admin" and not (u.get("employee_name") or "").strip():
            pass  # admin 可保持空 employee_name
        elif not (u.get("employee_name") or "").strip():
            u["employee_name"] = "戴雅利"
    return u


def install_users_from_persistent(registry: dict, loaded: dict | None) -> None:
    """从 data.json / MySQL 合并登录账号，并规范化 admin。"""
    for uid, uinfo in (loaded or {}).items():
        if "employee_name" in (uinfo or {}):
            employee_name = uinfo.get("employee_name") or ""
        elif uid == "admin":
            employee_name = ""
        else:
            employee_name = (uinfo or {}).get("name", uid) or uid
        entry = {
            "password": (uinfo or {}).get("password", ""),
            "name": (uinfo or {}).get("name", uid),
            "role": (uinfo or {}).get("role", "员工"),
            "employee_name": employee_name,
        }
        if (uinfo or {}).get("is_system"):
            entry["is_system"] = True
        registry[uid] = normalize_user_record(uid, entry)


def permission_lookup_name(
    user: dict,
    username: str,
    permission_data: dict,
) -> str:
    en = (user.get("employee_name") or "").strip()
    if en:
        return en
    un = (username or "").strip()
    name = (user.get("name") or "").strip()
    perms = permission_data.get("permissions", {})
    if name and name in perms:
        return name
    if un and un in perms:
        return un
    if user.get("is_system") or un.lower() == "admin":
        return "戴雅利"
    if (user.get("role") or "").strip() == "超级管理员":
        return "戴雅利"
    return name or un


def user_has_permission(
    user: dict | None,
    username: str,
    feature: str,
    permission_data: dict,
    *,
    sync_fn: Callable[[], None] | None = None,
    get_db_fn: Callable[[], Any] | None = None,
) -> bool:
    if not user:
        return False
    role = (user.get("role") or "").strip()
    if user.get("is_system") or role == "超级管理员":
        return True
    un = (username or "").strip().lower()
    if un in _SUPER_ADMIN_USERNAMES:
        return True
    if (user.get("employee_name") or "").strip() in _SUPER_ADMIN_EMPLOYEE_NAMES and role in (
        "超级管理员",
        "管理员",
        "管理",
        "",
    ):
        return True
    if un == "admin" and role in ("超级管理员", "管理员", ""):
        return True
    if sync_fn:
        sync_fn()
    # MySQL 仅作历史数据补全，不在每次鉴权时覆盖 admin 已保存的权限
    subject = permission_lookup_name(user, username, permission_data)
    row = migrate_perm_dict(dict(permission_data.get("permissions", {}).get(subject, {})))
    return bool(row.get(feature, False))
