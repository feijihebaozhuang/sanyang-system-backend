# -*- coding: utf-8 -*-
"""生产端公告：管理员发布，其他用户未读提醒。"""
from __future__ import annotations

import datetime
from typing import Any, Callable


def ensure_tables(get_db_fn: Callable) -> None:
    db = get_db_fn()
    cur = db.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS production_announcements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL DEFAULT '',
            content TEXT NOT NULL,
            created_by VARCHAR(64) DEFAULT '',
            is_active TINYINT NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS production_announcement_reads (
            id INT AUTO_INCREMENT PRIMARY KEY,
            announcement_id INT NOT NULL,
            username VARCHAR(64) NOT NULL,
            read_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_ann_user (announcement_id, username)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    db.commit()
    cur.close()
    db.close()


def list_active_for_user(get_db_fn: Callable, username: str) -> list[dict]:
    ensure_tables(get_db_fn)
    db = get_db_fn()
    cur = db.cursor()
    cur.execute(
        """
        SELECT a.id, a.title, a.content, a.created_by, a.created_at, a.updated_at,
               (r.id IS NOT NULL) AS is_read
        FROM production_announcements a
        LEFT JOIN production_announcement_reads r
          ON r.announcement_id = a.id AND r.username = %s
        WHERE a.is_active = 1
        ORDER BY a.updated_at DESC
        LIMIT 20
        """,
        (username,),
    )
    rows = cur.fetchall()
    cur.close()
    db.close()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "title": r["title"],
                "content": r["content"],
                "created_by": r["created_by"],
                "created_at": str(r["created_at"] or ""),
                "updated_at": str(r["updated_at"] or ""),
                "is_read": bool(r["is_read"]),
            }
        )
    return out


def unread_count(get_db_fn: Callable, username: str) -> int:
    ensure_tables(get_db_fn)
    db = get_db_fn()
    cur = db.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS c FROM production_announcements a
        LEFT JOIN production_announcement_reads r
          ON r.announcement_id = a.id AND r.username = %s
        WHERE a.is_active = 1 AND r.id IS NULL
        """,
        (username,),
    )
    row = cur.fetchone()
    cur.close()
    db.close()
    return int(row["c"] if row else 0)


def save_announcement(
    get_db_fn: Callable,
    *,
    title: str,
    content: str,
    created_by: str,
    ann_id: int | None = None,
) -> dict:
    ensure_tables(get_db_fn)
    db = get_db_fn()
    cur = db.cursor()
    if ann_id:
        cur.execute(
            "UPDATE production_announcements SET title=%s, content=%s, updated_at=NOW() WHERE id=%s",
            (title, content, ann_id),
        )
    else:
        cur.execute(
            "INSERT INTO production_announcements (title, content, created_by, is_active) VALUES (%s,%s,%s,1)",
            (title, content, created_by),
        )
        ann_id = cur.lastrowid
    db.commit()
    cur.close()
    db.close()
    return {"id": ann_id, "title": title, "content": content}


def mark_read(get_db_fn: Callable, username: str, announcement_id: int) -> None:
    ensure_tables(get_db_fn)
    db = get_db_fn()
    cur = db.cursor()
    cur.execute(
        """
        INSERT IGNORE INTO production_announcement_reads (announcement_id, username, read_at)
        VALUES (%s, %s, NOW())
        """,
        (announcement_id, username),
    )
    db.commit()
    cur.close()
    db.close()


def mark_all_read(get_db_fn: Callable, username: str) -> int:
    ensure_tables(get_db_fn)
    items = list_active_for_user(get_db_fn, username)
    for it in items:
        if not it.get("is_read"):
            mark_read(get_db_fn, username, int(it["id"]))
    return unread_count(get_db_fn, username)
