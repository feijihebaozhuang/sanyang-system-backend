# -*- coding: utf-8 -*-
"""员工与功能权限（employees / employee_permissions / users）— 3003 统一管理。"""
from __future__ import annotations

import copy
import hashlib
from typing import Any

import config_json
import permission_resolve as perm_resolve

PERM_FEATURES = [
    "首页",
    "订单生产进度",
    "扫码报工",
    "日报表",
    "数据看板",
    "刀模",
    "刀模库",
    "库存",
    "原材料",
    "快麦ERP",
    "员工",
    "权限管理",
    "报价",
    "实时订单",
]

DEFAULT_POSITIONS = ["超级管理员", "主管", "管理", "客服", "员工", "财务", "业务员"]


def _connect():
    from customer_order_store import connect

    return connect()


def load_permission_bundle(base_dir: str | None = None) -> dict[str, Any]:
    """读取 permission_data 权威视图（JSON/vault + MySQL 补全）。"""
    overlay = config_json.read_permission_overlay(base_dir)
    bundle: dict[str, Any] = {}
    for key in config_json.PERMISSION_JSON_KEYS:
        if key in overlay:
            bundle[key] = copy.deepcopy(overlay[key])
    if "processes" not in bundle:
        bundle["processes"] = []
    if "positions" not in bundle:
        bundle["positions"] = list(DEFAULT_POSITIONS)
    if "employees" not in bundle:
        bundle["employees"] = []
    if "permissions" not in bundle:
        bundle["permissions"] = {}
    if "employee_enabled" not in bundle:
        bundle["employee_enabled"] = {}
    if "role_permissions" not in bundle:
        bundle["role_permissions"] = {}
    if "employee_roles" not in bundle:
        bundle["employee_roles"] = {}

    perm_resolve.merge_employee_permissions_from_db(bundle, _connect)
    _merge_employees_from_mysql(bundle)
    _merge_users_from_mysql(bundle)
    return bundle


def _merge_employees_from_mysql(bundle: dict) -> None:
    try:
        db = _connect()
        cur = db.cursor()
        cur.execute("SELECT name, position, enabled FROM employees ORDER BY name")
        rows = cur.fetchall() or []
        cur.close()
        db.close()
    except Exception:
        return
    if not rows:
        return
    emps = [{"name": r["name"], "position": r.get("position") or ""} for r in rows]
    bundle["employees"] = emps
    enabled = bundle.setdefault("employee_enabled", {})
    for r in rows:
        enabled[r["name"]] = bool(r.get("enabled", 1))


def _merge_users_from_mysql(bundle: dict) -> None:
    try:
        db = _connect()
        cur = db.cursor()
        cur.execute(
            "SELECT username, display_name, role, employee_name, enabled "
            "FROM users ORDER BY username"
        )
        rows = cur.fetchall() or []
        cur.close()
        db.close()
    except Exception:
        bundle["users"] = []
        return
    bundle["users"] = [
        {
            "username": r["username"],
            "display_name": r.get("display_name") or r["username"],
            "role": r.get("role") or "员工",
            "employee_name": r.get("employee_name") or "",
            "enabled": bool(r.get("enabled", 1)),
        }
        for r in rows
    ]


def save_permission_bundle(data: dict, *, base_dir: str | None = None) -> dict[str, Any]:
    """保存到 MySQL + data.json + vault（与 3001/3002 读同一套数据）。"""
    bundle = load_permission_bundle(base_dir)
    for key in (
        "processes",
        "positions",
        "employees",
        "permissions",
        "employee_enabled",
        "role_permissions",
        "employee_roles",
        "production_material_mapping",
        "process_timeouts",
    ):
        if key in data:
            bundle[key] = copy.deepcopy(data[key])

    db = _connect()
    cur = db.cursor()
    try:
        for emp in bundle.get("employees") or []:
            name = (emp.get("name") or "").strip()
            if not name:
                continue
            pos = (emp.get("position") or "").strip()
            ena = bundle.get("employee_enabled", {}).get(name, True)
            cur.execute(
                """
                INSERT INTO employees (name, position, enabled)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE position=VALUES(position), enabled=VALUES(enabled)
                """,
                (name, pos, 1 if ena else 0),
            )

        perms = bundle.get("permissions") or {}
        for emp_name, feat_dict in perms.items():
            if not isinstance(feat_dict, dict):
                continue
            for pk, val in feat_dict.items():
                pk2 = pk
                if pk2 == perm_resolve._PERM_LEGACY_KEY:
                    pk2 = perm_resolve._PERM_CURRENT_KEY
                cur.execute(
                    """
                    INSERT INTO employee_permissions (employee_name, permission_key, enabled)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE enabled=VALUES(enabled)
                    """,
                    (emp_name, pk2, 1 if val else 0),
                )

        for emp_name, ena in (bundle.get("employee_enabled") or {}).items():
            cur.execute(
                "UPDATE employees SET enabled=%s WHERE name=%s",
                (1 if ena else 0, emp_name),
            )

        db.commit()
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"MySQL 保存失败: {e}") from e
    finally:
        cur.close()
        db.close()

    detail = config_json.write_permission_overlay_detail(
        bundle, base_dir=base_dir, keys=config_json.PERMISSION_JSON_KEYS
    )
    return {"success": True, "detail": detail}


def upsert_employee(name: str, position: str = "", *, enabled: bool = True) -> dict:
    name = (name or "").strip()
    if not name:
        raise ValueError("name 必填")
    db = _connect()
    cur = db.cursor()
    cur.execute(
        """
        INSERT INTO employees (name, position, enabled)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE position=VALUES(position), enabled=VALUES(enabled)
        """,
        (name, (position or "").strip(), 1 if enabled else 0),
    )
    db.commit()
    cur.close()
    db.close()
    return {"name": name, "position": position, "enabled": enabled}


def delete_employee(name: str) -> None:
    name = (name or "").strip()
    if not name:
        return
    db = _connect()
    cur = db.cursor()
    cur.execute("DELETE FROM employee_permissions WHERE employee_name=%s", (name,))
    cur.execute("DELETE FROM employees WHERE name=%s", (name,))
    db.commit()
    cur.close()
    db.close()


def list_users() -> list[dict]:
    try:
        db = _connect()
        cur = db.cursor()
        cur.execute(
            "SELECT username, display_name, role, employee_name, enabled "
            "FROM users ORDER BY username"
        )
        rows = cur.fetchall() or []
        cur.close()
        db.close()
        return [
            {
                "username": r["username"],
                "display_name": r.get("display_name") or r["username"],
                "role": r.get("role") or "",
                "employee_name": r.get("employee_name") or "",
                "enabled": bool(r.get("enabled", 1)),
            }
            for r in rows
        ]
    except Exception:
        return []


def upsert_user(
    username: str,
    *,
    password: str = "",
    display_name: str = "",
    role: str = "员工",
    employee_name: str = "",
    enabled: bool = True,
) -> dict:
    username = (username or "").strip()
    if not username:
        raise ValueError("username 必填")
    if username == "admin":
        raise ValueError("不可通过此接口修改系统 admin")
    db = _connect()
    cur = db.cursor()
    if password:
        pwd = hashlib.sha256(password.encode()).hexdigest()
        cur.execute(
            """
            INSERT INTO users (username, password, display_name, role, employee_name, enabled)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE password=VALUES(password), display_name=VALUES(display_name),
                role=VALUES(role), employee_name=VALUES(employee_name), enabled=VALUES(enabled)
            """,
            (
                username,
                pwd,
                display_name or username,
                role,
                employee_name,
                1 if enabled else 0,
            ),
        )
    else:
        cur.execute("SELECT username FROM users WHERE username=%s", (username,))
        exists = cur.fetchone()
        if not exists and not password:
            raise ValueError("新建账号需填写 password")
        cur.execute(
            """
            INSERT INTO users (username, password, display_name, role, employee_name, enabled)
            VALUES (%s, '', %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE display_name=VALUES(display_name),
                role=VALUES(role), employee_name=VALUES(employee_name), enabled=VALUES(enabled)
            """,
            (username, display_name or username, role, employee_name, 1 if enabled else 0),
        )
    db.commit()
    cur.close()
    db.close()
    return {
        "username": username,
        "display_name": display_name or username,
        "role": role,
        "employee_name": employee_name,
        "enabled": enabled,
    }
