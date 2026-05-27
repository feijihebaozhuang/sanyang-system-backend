# -*- coding: utf-8 -*-
"""3001 仅洋坑塘、3002 仅美丽湾 — 员工列表按 dept 过滤，避免两端口混显。"""
from __future__ import annotations

import json
import os
import re
import threading
from typing import Any

DEPT_CS = "洋坑塘运营部"
DEPT_PROD = "美丽湾工厂部"

_INDEX_LOCK = threading.Lock()
_NAME_DEPT_INDEX: dict[str, str] | None = None


def _repo_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _load_index_from_data_json() -> dict[str, str]:
    idx: dict[str, str] = {}
    path = os.path.join(_repo_root(), "data.json")
    if not os.path.isfile(path):
        return idx
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for emp in data.get("employees_master") or []:
            name = (emp.get("name") or "").strip()
            dept = (emp.get("dept") or "").strip()
            if name and dept:
                idx[name] = dept
    except Exception:
        pass
    return idx


def _load_index_from_production_defaults() -> dict[str, str]:
    idx: dict[str, str] = {}
    path = os.path.join(_repo_root(), "app_production.py")
    if not os.path.isfile(path):
        return idx
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for m in re.finditer(
            r'\{"name":\s*"([^"]+)"[^}]*"dept":\s*"([^"]+)"',
            text,
        ):
            idx[m.group(1)] = m.group(2)
    except Exception:
        pass
    return idx


def get_name_dept_index() -> dict[str, str]:
    global _NAME_DEPT_INDEX
    with _INDEX_LOCK:
        if _NAME_DEPT_INDEX is not None:
            return _NAME_DEPT_INDEX
        idx = _load_index_from_production_defaults()
        idx.update(_load_index_from_data_json())
        _NAME_DEPT_INDEX = idx
        return idx


def dept_of(emp: dict[str, Any], index: dict[str, str] | None = None) -> str:
    dept = (emp.get("dept") or emp.get("department") or "").strip()
    if dept:
        return dept
    name = (emp.get("name") or "").strip()
    if not name:
        return ""
    idx = index if index is not None else get_name_dept_index()
    return (idx.get(name) or "").strip()


def enrich_employee(emp: dict[str, Any], index: dict[str, str] | None = None) -> dict[str, Any]:
    idx = index if index is not None else get_name_dept_index()
    d = dept_of(emp, idx)
    if d and not emp.get("dept"):
        row = dict(emp)
        row["dept"] = d
        return row
    return emp


def is_yangkengtang(emp: dict[str, Any], index: dict[str, str] | None = None) -> bool:
    return "洋坑塘" in dept_of(emp, index)


def is_meiliwan(emp: dict[str, Any], index: dict[str, str] | None = None) -> bool:
    d = dept_of(emp, index)
    return "美丽湾" in d


def filter_cs_site(employees: list[dict[str, Any]]) -> list[dict[str, Any]]:
    idx = get_name_dept_index()
    out: list[dict[str, Any]] = []
    for emp in employees or []:
        row = enrich_employee(emp, idx)
        if is_yangkengtang(row, idx):
            out.append(row)
    return out


def filter_prod_site(employees: list[dict[str, Any]]) -> list[dict[str, Any]]:
    idx = get_name_dept_index()
    out: list[dict[str, Any]] = []
    for emp in employees or []:
        row = enrich_employee(emp, idx)
        if is_meiliwan(row, idx):
            out.append(row)
    return out
