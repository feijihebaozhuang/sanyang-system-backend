# -*- coding: utf-8 -*-
"""跨 Gunicorn worker 的订单同步互斥锁（MySQL GET_LOCK）。"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Iterator

_LOCK_NAME = (os.getenv("ORDER_SYNC_MYSQL_LOCK") or "sanyang_km_order_sync").strip()[:64]
_LOCK_WAIT_SEC = max(0, int(os.getenv("ORDER_SYNC_LOCK_WAIT_SEC", "2") or 2))


def _connect():
    import pymysql

    from settings import get_db_config

    cfg = dict(get_db_config())
    cfg.pop("autocommit", None)
    return pymysql.connect(**cfg, autocommit=True, cursorclass=pymysql.cursors.DictCursor)


@contextmanager
def order_sync_cluster_lock(*, wait_sec: int | None = None) -> Iterator[bool]:
    """
    集群内同一时刻只允许一个进程跑快麦拉单。
    yield True 表示已获锁；False 表示跳过（其它 worker 正在同步）。
    """
    wait = _LOCK_WAIT_SEC if wait_sec is None else max(0, int(wait_sec))
    conn = None
    cur = None
    acquired = False
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute("SELECT GET_LOCK(%s, %s)", (_LOCK_NAME, wait))
        row = cur.fetchone()
        acquired = bool(row and list(row.values())[0] == 1)
        yield acquired
    except Exception as ex:
        print(f"[订单同步] MySQL 锁不可用，本机继续同步: {ex}")
        yield True
    finally:
        if acquired and cur:
            try:
                cur.execute("SELECT RELEASE_LOCK(%s)", (_LOCK_NAME,))
            except Exception:
                pass
        if cur:
            cur.close()
        if conn:
            conn.close()


def lock_held_by_other() -> bool:
    """探测锁是否被占用（不等待）。"""
    with order_sync_cluster_lock(wait_sec=0) as got:
        return not got
