# -*- coding: utf-8 -*-
"""员工与功能权限（employees / employee_permissions / users）— 3003 统一管理。"""
from __future__ import annotations

import copy
import datetime
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


def load_employees_master(base_dir: str | None = None) -> list[dict[str, Any]]:
    """全量员工主数据：优先 data.json employees_master（含美丽湾/洋坑塘 dept/group）。"""
    raw = config_json.read_json_file(config_json.data_json_path(base_dir), {})
    master = raw.get("employees_master") if isinstance(raw, dict) else None
    if isinstance(master, list) and master:
        return copy.deepcopy(master)
    overlay = config_json.read_permission_overlay(base_dir)
    emps = overlay.get("employees")
    if isinstance(emps, list) and emps:
        return copy.deepcopy(emps)
    return []


def load_resigned_employees(base_dir: str | None = None) -> list[dict[str, Any]]:
    raw = config_json.read_json_file(config_json.data_json_path(base_dir), {})
    items = raw.get("resigned_employees") if isinstance(raw, dict) else None
    return copy.deepcopy(items) if isinstance(items, list) else []


def _persist_employees_master(
    employees: list[dict[str, Any]],
    *,
    base_dir: str | None = None,
    resigned: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """写入 employees_master + 同步 permission_data.employees 到 data.json/vault。"""
    updates: dict[str, Any] = {"employees_master": employees}
    if resigned is not None:
        updates["resigned_employees"] = resigned
    local_ok = config_json.write_data_json_partial(updates, base_dir=base_dir)
    overlay = config_json.read_permission_overlay(base_dir)
    overlay["employees"] = [
        {"name": e.get("name", ""), "position": e.get("position") or ""}
        for e in employees
        if e.get("name")
    ]
    detail = config_json.write_permission_overlay_detail(
        overlay, base_dir=base_dir, keys=frozenset({"employees"})
    )
    detail["employees_master_ok"] = local_ok
    return detail


def sync_permissions(bundle: dict[str, Any]) -> None:
    """与 3001 _sync_all_employees_perms 一致：补全新员工权限、清理离职残留。"""
    base = bundle.setdefault("permissions", {})
    for emp in bundle.get("employees") or []:
        name = emp.get("name") if isinstance(emp, dict) else emp
        if not name:
            continue
        if name == "戴雅利":
            if name not in base:
                base[name] = {}
            for f in PERM_FEATURES:
                base[name][f] = True
        elif name not in base:
            base[name] = {f: False for f in PERM_FEATURES}
        else:
            perm_resolve.migrate_perm_dict(base[name])
            for f in PERM_FEATURES:
                if f not in base[name]:
                    base[name][f] = False
    valid = {
        (e.get("name") if isinstance(e, dict) else e)
        for e in (bundle.get("employees") or [])
    }
    valid.discard(None)
    valid.discard("")
    for name in list(base.keys()):
        if name not in valid:
            del base[name]


def _merge_simple_into_master(
    master: list[dict[str, Any]], simple: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_name = {e["name"]: copy.deepcopy(e) for e in master if e.get("name")}
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for s in simple:
        name = (s.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        if name in by_name:
            row = by_name[name]
            if s.get("position"):
                row["position"] = s["position"]
        else:
            row = dict(s)
        out.append(row)
    for e in master:
        name = e.get("name")
        if name and name not in seen:
            out.append(copy.deepcopy(e))
    return out


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
    bundle["employees"] = load_employees_master(base_dir)
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
    sync_permissions(bundle)
    return bundle


def _merge_employees_from_mysql(bundle: dict) -> None:
    """仅同步 enabled；MySQL 有而主数据无的员工追加到列表（不覆盖美丽湾全量）。"""
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
    enabled = bundle.setdefault("employee_enabled", {})
    names = {e.get("name") for e in bundle.get("employees") or [] if e.get("name")}
    for r in rows:
        name = r["name"]
        enabled[name] = bool(r.get("enabled", 1))
        if name not in names:
            bundle.setdefault("employees", []).append(
                {"name": name, "position": r.get("position") or ""}
            )
            names.add(name)


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
        "permissions",
        "employee_enabled",
        "role_permissions",
        "employee_roles",
        "production_material_mapping",
        "process_timeouts",
    ):
        if key in data:
            bundle[key] = copy.deepcopy(data[key])
    if "employees" in data:
        bundle["employees"] = _merge_simple_into_master(
            bundle.get("employees") or [], data["employees"]
        )

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

    sync_permissions(bundle)
    detail = config_json.write_permission_overlay_detail(
        bundle, base_dir=base_dir, keys=config_json.PERMISSION_JSON_KEYS
    )
    master_detail = _persist_employees_master(
        bundle.get("employees") or [], base_dir=base_dir
    )
    detail.update(master_detail)
    return {"success": True, "detail": detail}


def list_employees_full() -> list[dict[str, Any]]:
    emps = load_employees_master()
    users = {u.get("employee_name"): u for u in list_users() if u.get("employee_name")}
    out = []
    for e in emps:
        row = dict(e)
        u = users.get(e.get("name", ""))
        if u:
            row["username"] = u.get("username", "")
            row["role"] = u.get("role", "")
        else:
            row["username"] = ""
            row["role"] = ""
        out.append(row)
    return out


def add_employee_full(
    name: str,
    *,
    position: str = "",
    group: str = "",
    phone: str = "",
    dept: str = "美丽湾工厂部",
    base_dir: str | None = None,
) -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise ValueError("员工姓名不能为空")
    emps = load_employees_master(base_dir)
    if any(e.get("name") == name for e in emps):
        raise ValueError(f"员工 {name} 已存在")
    emps.append(
        {
            "name": name,
            "position": (position or "").strip() or "员工",
            "group": (group or "").strip() or "其他",
            "phone": (phone or "").strip(),
            "dept": (dept or "").strip() or "美丽湾工厂部",
        }
    )
    db = _connect()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO employees (name, position, enabled) VALUES (%s, %s, 1) "
        "ON DUPLICATE KEY UPDATE position=VALUES(position), enabled=1",
        (name, (position or "").strip() or "员工"),
    )
    db.commit()
    cur.close()
    db.close()
    bundle = load_permission_bundle(base_dir)
    bundle["employees"] = emps
    sync_permissions(bundle)
    _persist_employees_master(emps, base_dir=base_dir)
    config_json.write_permission_overlay_detail(
        {"permissions": bundle.get("permissions"), "employee_enabled": bundle.get("employee_enabled")},
        base_dir=base_dir,
        keys=frozenset({"permissions", "employee_enabled"}),
    )
    return {"name": name}


def update_employee_full(
    old_name: str,
    *,
    name: str,
    position: str = "",
    group: str = "",
    phone: str = "",
    dept: str = "",
    base_dir: str | None = None,
) -> None:
    old_name = (old_name or "").strip()
    name = (name or "").strip()
    if not old_name or not name:
        raise ValueError("员工姓名不能为空")
    emps = load_employees_master(base_dir)
    target = next((e for e in emps if e.get("name") == old_name), None)
    if not target:
        raise ValueError(f"未找到员工 {old_name}")
    target["name"] = name
    if position is not None:
        target["position"] = str(position).strip() or "员工"
    if group is not None:
        target["group"] = str(group).strip() or "其他"
    if phone is not None:
        target["phone"] = str(phone).strip()
    if dept is not None and str(dept).strip():
        target["dept"] = str(dept).strip()
    if old_name != name:
        db = _connect()
        cur = db.cursor()
        cur.execute(
            "UPDATE employees SET name=%s, position=%s WHERE name=%s",
            (name, target.get("position", ""), old_name),
        )
        cur.execute(
            "UPDATE employee_permissions SET employee_name=%s WHERE employee_name=%s",
            (name, old_name),
        )
        cur.execute(
            "UPDATE users SET employee_name=%s, display_name=%s WHERE employee_name=%s",
            (name, name, old_name),
        )
        db.commit()
        cur.close()
        db.close()
    else:
        db = _connect()
        cur = db.cursor()
        cur.execute(
            "UPDATE employees SET position=%s WHERE name=%s",
            (target.get("position", ""), name),
        )
        db.commit()
        cur.close()
        db.close()
    bundle = load_permission_bundle(base_dir)
    perms = bundle.setdefault("permissions", {})
    if old_name != name and old_name in perms:
        perms[name] = perms.pop(old_name)
    ena = bundle.setdefault("employee_enabled", {})
    if old_name != name and old_name in ena:
        ena[name] = ena.pop(old_name)
    bundle["employees"] = emps
    sync_permissions(bundle)
    _persist_employees_master(emps, base_dir=base_dir)
    config_json.write_permission_overlay_detail(
        {"permissions": bundle.get("permissions"), "employee_enabled": bundle.get("employee_enabled")},
        base_dir=base_dir,
        keys=frozenset({"permissions", "employee_enabled"}),
    )


def resign_employee(name: str, *, operator: str = "", base_dir: str | None = None) -> None:
    name = (name or "").strip()
    if not name:
        raise ValueError("name 必填")
    emps = load_employees_master(base_dir)
    emp = next((e for e in emps if e.get("name") == name), None)
    resigned = load_resigned_employees(base_dir)
    if emp:
        resigned.append(
            {
                **copy.deepcopy(emp),
                "resigned_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "operator": operator or "admin",
            }
        )
    emps = [e for e in emps if e.get("name") != name]
    db = _connect()
    cur = db.cursor()
    cur.execute("UPDATE employees SET enabled=0 WHERE name=%s", (name,))
    cur.execute("DELETE FROM employee_permissions WHERE employee_name=%s", (name,))
    db.commit()
    cur.close()
    db.close()
    bundle = load_permission_bundle(base_dir)
    bundle["employees"] = emps
    perms = bundle.get("permissions") or {}
    if name in perms:
        del perms[name]
    bundle["permissions"] = perms
    _persist_employees_master(emps, base_dir=base_dir, resigned=resigned)
    config_json.write_permission_overlay_detail(
        {"permissions": perms},
        base_dir=base_dir,
        keys=frozenset({"permissions"}),
    )


def restore_resigned_employee(name: str, *, base_dir: str | None = None) -> None:
    name = (name or "").strip()
    resigned = load_resigned_employees(base_dir)
    rec = next((e for e in resigned if e.get("name") == name), None)
    resigned = [e for e in resigned if e.get("name") != name]
    emps = load_employees_master(base_dir)
    if rec and not any(e.get("name") == name for e in emps):
        row = {k: v for k, v in rec.items() if k not in ("resigned_time", "operator")}
        emps.append(row)
    db = _connect()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO employees (name, position, enabled) VALUES (%s, %s, 1) "
        "ON DUPLICATE KEY UPDATE enabled=1",
        (name, (rec or {}).get("position", "")),
    )
    db.commit()
    cur.close()
    db.close()
    bundle = load_permission_bundle(base_dir)
    bundle["employees"] = emps
    sync_permissions(bundle)
    _persist_employees_master(emps, base_dir=base_dir, resigned=resigned)
    config_json.write_permission_overlay_detail(
        {"permissions": bundle.get("permissions")},
        base_dir=base_dir,
        keys=frozenset({"permissions"}),
    )


def delete_resigned_record(name: str, *, base_dir: str | None = None) -> None:
    name = (name or "").strip()
    resigned = [e for e in load_resigned_employees(base_dir) if e.get("name") != name]
    config_json.write_data_json_partial(
        {"resigned_employees": resigned}, base_dir=base_dir
    )


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


def list_login_accounts() -> list[dict[str, Any]]:
    """员工主数据 + 登录账号合并视图（3003 登录账号页）。"""
    emps = load_employees_master()
    users = list_users()
    by_emp: dict[str, dict] = {}
    emp_names: set[str] = set()
    for e in emps:
        n = (e.get("name") or "").strip()
        if n:
            emp_names.add(n)
    for u in users:
        en = (u.get("employee_name") or "").strip()
        if en:
            by_emp[en] = u
    rows: list[dict[str, Any]] = []
    for e in emps:
        name = (e.get("name") or "").strip()
        if not name:
            continue
        u = by_emp.get(name)
        rows.append(
            {
                "employee_name": name,
                "username": u["username"] if u else "",
                "display_name": (u.get("display_name") if u else "") or name,
                "role": (u.get("role") if u else "") or "员工",
                "enabled": bool(u.get("enabled", True)) if u else False,
                "has_login": bool(u),
                "dept": e.get("dept") or "",
                "position": e.get("position") or "",
            }
        )
    for u in users:
        if u.get("username") == "admin":
            continue
        en = (u.get("employee_name") or "").strip()
        if en and en in emp_names:
            continue
        rows.append(
            {
                "employee_name": en,
                "username": u.get("username") or "",
                "display_name": u.get("display_name") or u.get("username") or "",
                "role": u.get("role") or "",
                "enabled": bool(u.get("enabled", True)),
                "has_login": True,
                "orphan": True,
                "dept": "",
                "position": "",
            }
        )
    return rows


def sync_login_accounts_from_employees() -> dict[str, Any]:
    """将 users.display_name 与 employee_name 对齐（员工主数据为准）。"""
    emp_names = {
        (e.get("name") or "").strip()
        for e in load_employees_master()
        if (e.get("name") or "").strip()
    }
    fixed = 0
    for u in list_users():
        un = u.get("username") or ""
        if un == "admin":
            continue
        en = (u.get("employee_name") or "").strip()
        if not en or en not in emp_names:
            continue
        if (u.get("display_name") or "").strip() != en:
            upsert_user(
                un,
                display_name=en,
                role=u.get("role") or "员工",
                employee_name=en,
                enabled=bool(u.get("enabled", True)),
            )
            fixed += 1
    return {"fixed_display_names": fixed}


def upsert_user(
    username: str,
    *,
    old_username: str = "",
    password: str = "",
    display_name: str = "",
    role: str = "员工",
    employee_name: str = "",
    enabled: bool = True,
) -> dict:
    username = (username or "").strip()
    old_username = (old_username or "").strip()
    if not username:
        raise ValueError("username 必填")
    if username == "admin" or old_username == "admin":
        raise ValueError("不可通过此接口修改系统 admin")
    db = _connect()
    cur = db.cursor()
    try:
        if old_username and old_username != username:
            cur.execute(
                "SELECT username, password, display_name, role, employee_name, enabled "
                "FROM users WHERE username=%s",
                (old_username,),
            )
            old_row = cur.fetchone()
            if not old_row:
                raise ValueError(f"未找到原登录账号 {old_username}")
            cur.execute("SELECT username FROM users WHERE username=%s", (username,))
            if cur.fetchone():
                raise ValueError(f"登录账号 {username} 已被占用")
            pwd = (
                hashlib.sha256(password.encode()).hexdigest()
                if password
                else old_row.get("password") or ""
            )
            disp = display_name or old_row.get("display_name") or username
            rol = role or old_row.get("role") or "员工"
            en = employee_name if employee_name != "" else (old_row.get("employee_name") or "")
            ena = 1 if enabled else 0
            cur.execute("DELETE FROM users WHERE username=%s", (old_username,))
            cur.execute(
                """
                INSERT INTO users (username, password, display_name, role, employee_name, enabled)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (username, pwd, disp, rol, en, ena),
            )
            db.commit()
            return {
                "username": username,
                "display_name": disp,
                "role": rol,
                "employee_name": en,
                "enabled": bool(ena),
            }

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
    finally:
        cur.close()
        db.close()
    en = employee_name
    if en and not display_name:
        display_name = en
    return {
        "username": username,
        "display_name": display_name or username,
        "role": role,
        "employee_name": en,
        "enabled": enabled,
    }
