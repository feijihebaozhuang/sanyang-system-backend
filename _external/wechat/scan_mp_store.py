# -*- coding: utf-8 -*-
"""生产报工小程序（scan-weapp）微信 openid 与 users 表绑定。"""
from __future__ import annotations

from typing import Any


def _connect():
    from customer_order_store import connect

    return connect()


def _ensure_column(cur, table: str, column: str, ddl: str) -> None:
    cur.execute(f"SHOW COLUMNS FROM `{table}` LIKE %s", (column,))
    if not cur.fetchone():
        cur.execute(ddl)


def ensure_schema() -> None:
    db = _connect()
    cur = db.cursor()
    try:
        _ensure_column(
            cur,
            "users",
            "scan_wx_openid",
            "ALTER TABLE users ADD COLUMN scan_wx_openid "
            "VARCHAR(128) NOT NULL DEFAULT '' "
            "COMMENT '生产报工小程序微信openid' AFTER enabled",
        )
        cur.execute("SHOW INDEX FROM users WHERE Key_name='idx_users_scan_wx_openid'")
        if not cur.fetchone():
            try:
                cur.execute(
                    "CREATE INDEX idx_users_scan_wx_openid ON users (scan_wx_openid)"
                )
            except Exception:
                pass
        db.commit()
    finally:
        cur.close()
        db.close()


def find_user_by_scan_openid(openid: str) -> dict[str, Any] | None:
    openid = (openid or "").strip()
    if not openid:
        return None
    ensure_schema()
    db = _connect()
    cur = db.cursor()
    try:
        cur.execute(
            """
            SELECT username, password, display_name, role, employee_name, enabled
            FROM users
            WHERE scan_wx_openid=%s AND enabled=1
            LIMIT 1
            """,
            (openid,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        db.close()


def bind_scan_openid(username: str, openid: str) -> None:
    username = (username or "").strip()
    openid = (openid or "").strip()
    if not username or not openid:
        raise ValueError("username 与 openid 必填")
    ensure_schema()
    db = _connect()
    cur = db.cursor()
    try:
        cur.execute(
            "SELECT username FROM users WHERE scan_wx_openid=%s AND username<>%s LIMIT 1",
            (openid, username),
        )
        if cur.fetchone():
            raise ValueError("该微信已绑定其他账号")
        cur.execute(
            "UPDATE users SET scan_wx_openid=%s WHERE username=%s",
            (openid, username),
        )
        if cur.rowcount < 1:
            raise ValueError("账号不存在，请先在管理后台创建登录账号")
        db.commit()
    finally:
        cur.close()
        db.close()
