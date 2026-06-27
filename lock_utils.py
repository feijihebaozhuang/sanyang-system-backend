# -*- coding: utf-8 -*-
"""
跨进程文件锁工具：保护 data.json / km_token.json / quote_data.json 写操作不被并发覆盖。
"""
from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path
from typing import Iterator


_LOCK_DIR_NAME = ".sanyang_locks"


def _lock_dir() -> Path:
    """锁文件统一存放在临时目录，避免在项目目录产生 .lock 文件。"""
    d = Path(os.getenv("SANYANG_LOCK_DIR", "")).resolve()
    if d.is_dir():
        return d
    d = Path(os.getenv("TMPDIR", "/tmp")) / _LOCK_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


@contextlib.contextmanager
def file_lock(target_path: str | Path, *, timeout: float = 10.0, retry_interval: float = 0.1) -> Iterator[bool]:
    """
    用文件锁（无 fcntl/msvcrt 依赖）保护跨进程写操作。
    原理：创建 .sanyang.lock 标记文件，创建成功即获得锁，删除即释放。
    yield True = 获得锁；yield False = 超时未获得锁。
    """
    target = Path(target_path).resolve()
    lock_file = _lock_dir() / f"{target.name}.{hash(str(target))}.lock"
    deadline = time.time() + timeout
    acquired = False

    try:
        while time.time() < deadline:
            try:
                fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                try:
                    lock_file.write_text(str(os.getpid()), encoding="utf-8")
                except OSError:
                    pass
                acquired = True
                break
            except FileExistsError:
                try:
                    old_pid = int(lock_file.read_text(encoding="utf-8").strip())
                    is_zombie = not _pid_alive(old_pid)
                except (OSError, ValueError, OSError):
                    is_zombie = False
                if is_zombie:
                    lock_file.unlink(missing_ok=True)
                    continue
                time.sleep(retry_interval)
        yield acquired
    finally:
        if acquired:
            try:
                lock_file.unlink(missing_ok=True)
            except OSError:
                pass


def _pid_alive(pid: int) -> bool:
    """检查进程是否存活（POSIX / Windows）。"""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
    except AttributeError:
        return True


def safe_write_json(path: str | Path, data: object, *, timeout: float = 10.0) -> bool:
    """
    加锁 + 原子写 JSON 文件。
    1. 获取文件锁
    2. 写临时文件
    3. os.replace 原子覆盖目标文件
    返回 True=成功，False=超时或失败。
    """
    import json as _json

    target = Path(path).resolve()
    tmp = target.with_suffix(f".tmp.{os.getpid()}")
    with file_lock(target, timeout=timeout) as acquired:
        if not acquired:
            return False
        try:
            with tmp.open("w", encoding="utf-8") as f:
                _json.dump(data, f, ensure_ascii=False, indent=2)
            tmp.replace(target)
            return True
        except OSError as e:
            print(f"[lock_utils] 写文件失败 {target}: {e}")
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return False
