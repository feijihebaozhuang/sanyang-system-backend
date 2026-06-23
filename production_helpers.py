# -*- coding: utf-8 -*-
"""生产端：订单缓存、工序树、扫码报工、报表统计（真实数据）。"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

import pymysql

_scan_table_ready = False


def ensure_scan_logs_table(db_config: dict) -> None:
    global _scan_table_ready
    if _scan_table_ready:
        return
    try:
        db = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
        cur = db.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id VARCHAR(64) NOT NULL,
                step_name VARCHAR(128) NOT NULL,
                worker VARCHAR(64) DEFAULT '',
                status VARCHAR(32) DEFAULT '已完成',
                extra_data TEXT DEFAULT NULL COMMENT '报工额外字段值(JSON)',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_order (order_id),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        # 兼容旧表：补 extra_data 列（已有则忽略）
        try:
            cur.execute(
                "ALTER TABLE scan_logs "
                "ADD COLUMN extra_data TEXT DEFAULT NULL "
                "COMMENT '报工额外字段值(JSON)'"
            )
            db.commit()
        except Exception:
            db.rollback()
        db.commit()
        cur.close()
        db.close()
        _scan_table_ready = True
    except Exception as e:
        print(f"[scan_logs] 建表失败: {e}")


def get_step_fields(process_tree: list, step_name: str) -> list[dict]:
    """从工序树查找指定工序的 fields 定义，返回 [] 表示无额外字段。"""
    for dept in process_tree:
        if not isinstance(dept, dict):
            continue
        for s in dept.get("steps") or []:
            if isinstance(s, dict) and s.get("name") == step_name:
                return s.get("fields") or []
    return []


def get_all_step_fields(process_tree: list) -> dict[str, list[dict]]:
    """获取所有工序的字段定义 {工序名: [fields]}。"""
    result = {}
    for dept in process_tree:
        if not isinstance(dept, dict):
            continue
        for s in dept.get("steps") or []:
            if isinstance(s, dict) and s.get("fields"):
                result[s["name"]] = s["fields"]
    return result


def order_date_key(o: dict) -> str:
    for field in ("pay_time", "created", "consign_time", "updTime", "updated"):
        raw = str(o.get(field) or "").strip()
        if not raw:
            continue
        if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
            return raw[:10]
        digits = "".join(c for c in raw if c.isdigit())
        if len(digits) >= 8:
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return ""


def order_on_date(o: dict, date_yyyy_mm_dd: str) -> bool:
    return order_date_key(o) == date_yyyy_mm_dd


def filter_orders_by_range(orders: list, range_type: str) -> list:
    now = datetime.now()
    today = now.date()
    out = []
    for o in orders:
        dk = order_date_key(o)
        if not dk:
            continue
        try:
            od = datetime.strptime(dk, "%Y-%m-%d").date()
        except ValueError:
            continue
        if range_type == "live":
            if od != today:
                continue
        elif range_type == "yesterday":
            if od != today - timedelta(days=1):
                continue
        elif range_type == "week":
            if od < today - timedelta(days=today.weekday()):
                continue
        elif range_type == "month":
            if od.year != today.year or od.month != today.month:
                continue
        elif range_type == "last30":
            if od < today - timedelta(days=29):
                continue
        elif range_type == "quarter":
            qm = ((today.month - 1) // 3) * 3 + 1
            if od < date(today.year, qm, 1):
                continue
        else:
            if od < today - timedelta(days=6):
                continue
        out.append(o)
    return out


def template_steps_for_order(process_tree: list, order_type: str) -> list[dict]:
    dept = get_process_dept(process_tree, order_type)
    return steps_from_dept(dept)


def merge_flow_with_tree(
    existing_steps: list[dict],
    process_tree: list,
    order_type: str,
) -> list[dict]:
    """按工序树重建步骤列表，保留同名工序的完成状态。"""
    template = template_steps_for_order(process_tree, order_type)
    done_map = {}
    person_map = {}
    time_map = {}
    for s in existing_steps or []:
        name = s.get("step") or s.get("name") or ""
        if not name:
            continue
        if s.get("done"):
            done_map[name] = True
            person_map[name] = s.get("person") or ""
            time_map[name] = s.get("time") or "-"
    merged = []
    for t in template:
        nm = t.get("step") or ""
        merged.append(
            {
                "step": nm,
                "done": bool(done_map.get(nm)),
                "time": time_map.get(nm, "-"),
                "person": person_map.get(nm, ""),
            }
        )
    return merged


def resolve_km_sid(o: dict) -> str:
    """快麦 ERP 内部短单号（sid），勿把平台 tid 当内部单号。"""
    tid = str(o.get("tid") or o.get("platform_tid") or "").strip()
    for key in ("km_sid", "sid"):
        v = str(o.get(key) or "").strip()
        if v and v != tid and len(v) <= 14:
            return v
    so = str(o.get("so_id") or "").strip()
    if so and so != tid and len(so) <= 14:
        return so
    try:
        import km_api as _km

        r = _km.km_resolve_internal_so_id(o)
        if r and r != tid and len(r) <= 14:
            return r
    except ImportError:
        pass
    return ""


def internal_order_id(o: dict) -> str:
    """快麦内部单号；优先短 sid，避免旧缓存把平台 tid 写在 so_id。"""
    try:
        import km_api as _km

        _km.km_normalize_so_id_fields(o)
    except ImportError:
        pass
    sid = resolve_km_sid(o)
    if sid:
        return sid
    return str(o.get("so_id") or o.get("km_sid") or "").strip()


def km_sid_needs_km_refresh(o: dict) -> bool:
    """内部单号缺失或误用平台 tid 时需实时查快麦。"""
    tid = str(o.get("tid") or o.get("platform_tid") or "").strip()
    sid = resolve_km_sid(o)
    if not sid:
        return True
    if tid and sid == tid:
        return True
    if len(sid) > 14:
        return True
    return False


def fetch_km_trade_for_scan(query: str) -> dict | None:
    """扫码报工：按平台 tid 或内部 sid 实时查快麦（已完成/已发货单常不在待发货缓存）。"""
    q = (query or "").strip()
    if not q:
        return None
    try:
        import km_api as _km
        from datetime import datetime, timedelta

        end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d %H:%M:%S")
        base = {
            "start_time": start,
            "end_time": end,
            "page_no": 1,
            "page_size": 1,
            "time_type": "upd_time",
        }
        tries: list[dict] = []
        if len(q) > 14:
            tries.append({**base, "tid": q})
        else:
            tries.append({**base, "sid": q})
            tries.append({**base, "tid": q})
        for kw in tries:
            res = _km.km_outstock_simple_page(**kw)
            batch = res.get("list") or []
            if batch:
                return batch[0]
    except Exception as e:
        print(f"[fetch_km_trade_for_scan] {e}")
    return None


def order_dict_from_km_trade(raw_o: dict, query: str) -> dict:
    """快麦 trade → 扫码报工用订单 dict。"""
    import km_api as _km

    sid = _km.km_resolve_internal_so_id(raw_o) or str(raw_o.get("sid") or "").strip()
    tid = str(raw_o.get("tid") or "").strip()
    if not tid and len((query or "").strip()) > 14:
        tid = (query or "").strip()
    items = []
    for it in raw_o.get("orders") or []:
        items.append(
            {
                "name": it.get("title", ""),
                "spec": it.get("skuPropertiesName", ""),
                "qty": int(it.get("num") or 0),
                "price": str(it.get("price") or "0"),
            }
        )
    sys_status = str(raw_o.get("sysStatus") or raw_o.get("status") or "").strip()
    label = _km.KM_SYS_STATUS_LABEL.get(sys_status, sys_status) or sys_status
    return {
        "items": items,
        "so_id": sid,
        "km_sid": sid,
        "tid": tid,
        "order_status": sys_status,
        "status_label": label,
        "shop_name": (raw_o.get("warehouseName") or raw_o.get("shopName") or "").replace("仓库", ""),
        "receiver_address": "",
        "seller_memo": "",
        "buyer_memo": "",
        "receiver_province": "",
        "receiver_city": "",
    }


def merge_scan_order_sources(km_hack: dict, cache_o: dict | None) -> dict:
    """快麦实时数据优先 sid/状态；缓存补商品行与备注。"""
    out = dict(km_hack)
    if not cache_o:
        return out
    if not out.get("items") and cache_o.get("items"):
        out["items"] = cache_o["items"]
    for key in (
        "seller_memo",
        "buyer_memo",
        "receiver_address",
        "receiver_province",
        "receiver_city",
        "refund_status",
        "refund_detail",
    ):
        if not out.get(key) and cache_o.get(key):
            out[key] = cache_o[key]
    return out


def load_cache_orders(cache_file: str | None = None, *, finalize: bool = True) -> list[dict]:
    del cache_file
    try:
        import order_cache_store as ocs

        orders, _status, _meta = ocs.load_orders_for_api(finalize=finalize)
        return orders
    except Exception as e:
        print(f"[load_cache_orders] MySQL 读取失败: {e}")
        return []


def item_buyer_attrs(it: dict) -> str:
    """子单行买家下单 SKU 属性（展示用 display，不读商品标题 name）。"""
    if not isinstance(it, dict):
        return ""
    d = (
        it.get("platform_spec_raw")
        or it.get("display")
        or it.get("platform_attrs")
        or it.get("spec")
        or ""
    )
    d = str(d).strip()
    if d:
        return d
    try:
        from km_api import km_collect_item_raw_attrs, km_item_for_resolve

        return km_collect_item_raw_attrs(km_item_for_resolve(it))
    except ImportError:
        return ""


def infer_order_type(o: dict) -> str:
    """按订单内各子单买家属性判断类型（飞机盒/纸箱等），不用商品标题。"""
    import production_spec as pspec

    parts: list[str] = []
    for it in o.get("items") or []:
        if not isinstance(it, dict):
            continue
        attrs = item_buyer_attrs(it)
        extra: list[str] = []
        kmp = it.get("km_product_dims") or {}
        if isinstance(kmp, dict) and kmp.get("material_hint"):
            extra.append(str(kmp["material_hint"]))
        for key in ("production_spec", "display", "spec"):
            v = (it.get(key) or "").strip()
            if v:
                extra.append(v)
                break
        blob_part = " ".join(x for x in [attrs, *extra] if x)
        if blob_part:
            parts.append(blob_part)
    blob = " ".join(parts)
    if pspec.attrs_indicate_carton(blob):
        return "纸箱"
    if "扣底盒" in blob or "双插盒" in blob:
        return "扣底盒"
    if "飞机盒" in blob:
        return "飞机盒"
    if "纸箱" in blob:
        return "纸箱"
    if "现货" in blob:
        return "现货"
    if "带扣" in blob:
        return "扣底盒"
    return "飞机盒"


def get_process_dept(process_tree: list, order_type: str) -> dict | None:
    if not process_tree:
        return None
    if not isinstance(process_tree[0], dict) or "dept" not in process_tree[0]:
        return None
    if order_type == "纸箱":
        for d in process_tree:
            if "纸箱" in (d.get("dept") or ""):
                return d
    else:
        for d in process_tree:
            dept = d.get("dept") or ""
            if "美丽湾" in dept or "飞机盒" in dept:
                return d
    return process_tree[0] if process_tree else None


def steps_from_dept(dept: dict | None) -> list[dict]:
    if not dept or not dept.get("steps"):
        return [{"step": "客服接单", "done": False, "time": "-", "person": ""}]
    out = []
    for s in dept["steps"]:
        name = s["name"] if isinstance(s, dict) else str(s)
        out.append({"step": name, "done": False, "time": "-", "person": ""})
    return out


def parse_flow_steps(raw: Any) -> list[dict]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = []
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if isinstance(item, dict):
            name = item.get("step") or item.get("name") or ""
            out.append(
                {
                    "step": name,
                    "done": bool(item.get("done")),
                    "time": item.get("time") or "-",
                    "person": item.get("person") or "",
                }
            )
        elif isinstance(item, str):
            out.append({"step": item, "done": False, "time": "-", "person": ""})
    return out


def flow_steps_to_json(steps: list[dict]) -> str:
    payload = []
    for s in steps:
        payload.append(
            {
                "name": s.get("step") or s.get("name"),
                "done": bool(s.get("done")),
                "time": s.get("time") or "-",
                "person": s.get("person") or "",
            }
        )
    return json.dumps(payload, ensure_ascii=False)


def get_flow_row(db_config: dict, order_id: str) -> dict | None:
    try:
        db = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
        cur = db.cursor()
        cur.execute("SELECT * FROM production_flows WHERE order_id=%s", (order_id,))
        row = cur.fetchone()
        cur.close()
        db.close()
        return row
    except Exception:
        return None


def _delete_flow_row(db_config: dict, order_id: str) -> None:
    try:
        db = pymysql.connect(**db_config)
        cur = db.cursor()
        cur.execute("DELETE FROM production_flows WHERE order_id=%s", (order_id,))
        db.commit()
        cur.close()
        db.close()
    except Exception:
        pass


def save_flow_row(
    db_config: dict,
    order_id: str,
    order_type: str,
    steps: list[dict],
) -> None:
    steps_json = flow_steps_to_json(steps)
    done_count = sum(1 for s in steps if s.get("done"))
    total = len(steps) or 1
    status = "done" if done_count >= total else "active"
    idx = done_count if done_count < total else total - 1
    try:
        db = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
        cur = db.cursor()
        cur.execute("SELECT id FROM production_flows WHERE order_id=%s", (order_id,))
        exists = cur.fetchone()
        if exists:
            cur.execute(
                """
                UPDATE production_flows
                SET product_type=%s, steps_json=%s, current_step_index=%s,
                    total_steps=%s, status=%s, updated_at=NOW()
                WHERE order_id=%s
                """,
                (order_type, steps_json, idx, total, status, order_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO production_flows
                (id, order_id, product_type, steps_json, current_step_index, total_steps, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (order_id, order_id, order_type, steps_json, idx, total, status),
            )
        db.commit()
        cur.close()
        db.close()
    except Exception as e:
        print(f"[production_flows] 保存失败: {e}")


def resync_active_flows_from_tree(db_config: dict, process_tree: list) -> int:
    """未完工工单按工序树重建步骤，保留同名工序完成状态。"""
    updated = 0
    try:
        db = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
        cur = db.cursor()
        cur.execute("SELECT order_id, product_type, steps_json FROM production_flows WHERE status='active'")
        rows = cur.fetchall()
        cur.close()
        db.close()
        for row in rows:
            oid = row.get("order_id") or ""
            order_type = row.get("product_type") or "飞机盒"
            existing = parse_flow_steps(row.get("steps_json"))
            merged = merge_flow_with_tree(existing, process_tree, order_type)
            old_names = [s.get("step") for s in existing]
            new_names = [s.get("step") for s in merged]
            if old_names != new_names or len(existing) != len(merged):
                save_flow_row(db_config, oid, order_type, merged)
                updated += 1
    except Exception as e:
        print(f"[resync_active_flows] {e}")
    return updated


def get_or_create_flow_steps(
    db_config: dict,
    process_tree: list,
    order_id: str,
    order_type: str,
    *,
    order: dict | None = None,
    order_routes: list | None = None,
    force_refresh: bool = False,
) -> list[dict]:
    if not force_refresh:
        row = get_flow_row(db_config, order_id)
        if row:
            steps = parse_flow_steps(row.get("steps_json"))
            if steps:
                return steps
    if force_refresh:
        _delete_flow_row(db_config, order_id)
    steps = match_order_route_steps(order, process_tree, order_routes)
    if not steps:
        dept = get_process_dept(process_tree, order_type)
        steps = steps_from_dept(dept)
    save_flow_row(db_config, order_id, order_type, steps)
    return steps


def match_order_route_steps(
    order: dict | None,
    process_tree: list,
    order_routes: list | None,
) -> list[dict] | None:
    """按订单路由规则匹配产线步骤（多部门 flow_template），供 3002/3003 共用。"""
    if not order or not order_routes:
        return None
    import re as _re
    for rule in order_routes:
        conds = rule.get("conditions")
        if not conds:
            cond = rule.get("condition")
            if cond:
                conds = [cond]
        if not conds:
            continue
        all_match = True
        for cond in conds:
            field = (cond.get("field") or "").strip()
            pattern = (cond.get("pattern") or "").strip()
            if not field or not pattern:
                all_match = False
                break
            val = None
            if field == "order_type":
                val = infer_order_type(order)
            elif field.startswith("items."):
                parts = field.split(".")
                if parts[0] == "items" and len(parts) >= 3:
                    try:
                        idx = int(parts[1])
                    except ValueError:
                        val = None
                    else:
                        items = order.get("items") or []
                        if idx < len(items):
                            item = items[idx]
                            key = parts[2]
                            val = str(item.get(key) or "")
                            if not val:
                                kmd = item.get("km_product_dims") or {}
                                val = str(kmd.get(key) or "")
                            if not val:
                                pa = item.get("platform_attrs") or {}
                                val = str(pa.get(key) or "")
                            if key == "qty" and not val:
                                val = str(item.get("num") or item.get("qty") or "")
            else:
                val = str(order.get(field) or "")
            if not val or not _re.search(pattern, val, _re.IGNORECASE):
                all_match = False
                break
        if not all_match:
            continue
        # 匹配成功，取 flow_template
        ft = rule.get("flow_template")
        if ft and isinstance(ft, list) and ft:
            out = []
            ft_depts = [d.strip() for d in ft if isinstance(d, str)]
            for dept in process_tree:
                if isinstance(dept, dict) and dept.get("dept") in ft_depts:
                    for s in (dept.get("steps") or []):
                        if isinstance(s, dict):
                            out.append({
                                "step": s.get("name", ""),
                                "dept": dept.get("dept", ""),
                                "done": False,
                                "time": "-",
                                "person": "",
                            })
            if out:
                return out
        # 或 process_dept
        match_dept = rule.get("process_dept")
        if match_dept and isinstance(match_dept, str):
            for dept in process_tree:
                if isinstance(dept, dict) and dept.get("dept") == match_dept:
                    return steps_from_dept(dept)
    return None


def find_order_in_cache(orders: list[dict], query: str) -> dict | None:
    q = (query or "").strip()
    if not q:
        return None
    ql = q.lower()
    for o in orders:
        oid = internal_order_id(o)
        tid = str(o.get("tid") or o.get("platform_tid") or "")
        if q == oid or q == tid or ql in oid.lower() or (tid and ql in tid.lower()):
            return o
    return None


def build_production_orders(
    cache_file: str,
    db_config: dict,
    process_tree: list,
    order_extra: dict,
) -> list[dict]:
    orders_data = []
    for o in load_cache_orders(cache_file):
        oid = internal_order_id(o)
        if not oid:
            continue
        order_type = infer_order_type(o)
        flow = get_or_create_flow_steps(db_config, process_tree, oid, order_type)
        specs = []
        product_parts = []
        for item in o.get("items") or []:
            spec = (item.get("spec") or "").strip()
            qty = int(item.get("qty") or 0)
            specs.append({"spec": spec, "qty": qty})
            label = spec or (item.get("name") or "")[:40]
            if label:
                product_parts.append(f"{label} x{qty}")
        addr = o.get("receiver_address") or ""
        parts = addr.split() if addr else []
        ex = order_extra.get(oid, {})
        orders_data.append(
            {
                "inner_id": oid,
                "km_sid": resolve_km_sid(o) or oid,
                "tid": o.get("tid") or o.get("platform_tid") or "",
                "store": o.get("shop_name") or "",
                "province": o.get("receiver_province") or (parts[0] if parts else ""),
                "city": o.get("receiver_city") or (parts[1] if len(parts) > 1 else ""),
                "specs": specs,
                "product": "; ".join(product_parts[:3]) or "?",
                "seller_memo": o.get("seller_memo") or "",
                "buyer_memo": o.get("buyer_memo") or "",
                "qty": sum(i.get("qty", 0) for i in (o.get("items") or [])),
                "type": order_type,
                "status": o.get("order_status") or o.get("status") or "",
                "status_label": o.get("status_label") or "",
                "urgent": bool(ex.get("urgent")),
                "flow": flow,
            }
        )
    return orders_data


def build_production_order_one(
    cache_file: str,
    db_config: dict,
    process_tree: list,
    order_extra: dict,
    query: str,
    *,
    raw: dict | None = None,
) -> dict | None:
    """按单号查一条生产订单（扫码报工小程序用，避免拉全量列表）。"""
    o = raw
    if o is None:
        orders = load_cache_orders(cache_file)
        o = find_order_in_cache(orders, query)
    if not o:
        return None
    oid = internal_order_id(o)
    km_sid = resolve_km_sid(o) or oid
    order_type = infer_order_type(o)
    flow = get_or_create_flow_steps(db_config, process_tree, oid, order_type)
    specs = []
    product_parts = []
    for item in o.get("items") or []:
        spec = (item.get("spec") or "").strip()
        qty = int(item.get("qty") or 0)
        specs.append({"spec": spec, "qty": qty})
        label = spec or (item.get("name") or "")[:40]
        if label:
            product_parts.append(f"{label} x{qty}")
    addr = o.get("receiver_address") or ""
    parts = addr.split() if addr else []
    ex = order_extra.get(oid, {})
    return {
        "inner_id": oid,
        "km_sid": km_sid,
        "tid": o.get("tid") or o.get("platform_tid") or "",
        "store": o.get("shop_name") or "",
        "province": o.get("receiver_province") or (parts[0] if parts else ""),
        "city": o.get("receiver_city") or (parts[1] if len(parts) > 1 else ""),
        "specs": specs,
        "product": "; ".join(product_parts[:3]) or "?",
        "seller_memo": o.get("seller_memo") or "",
        "buyer_memo": o.get("buyer_memo") or "",
        "qty": sum(i.get("qty", 0) for i in (o.get("items") or [])),
        "type": order_type,
        "status": o.get("order_status") or o.get("status") or "",
        "status_label": o.get("status_label") or "",
        "urgent": bool(ex.get("urgent")),
        "flow": flow,
    }


def build_single_order_from_dict(
    raw: dict,
    db_config: dict,
    process_tree: list,
    order_extra: dict,
) -> dict | None:
    """从构造好的订单dict构建生产订单工序（扫码报工缓存找不到时的备用路径）。"""
    oid = internal_order_id(raw)
    if not oid:
        return None
    order_type = infer_order_type(raw)
    flow = get_or_create_flow_steps(db_config, process_tree, oid, order_type)
    specs = []
    contains_miandian = False
    for item in raw.get("items") or []:
        spec = (item.get("spec") or "").strip()
        qty = int(item.get("qty") or 0)
        specs.append({"spec": spec, "qty": qty})
        if "棉" in spec or "棉" in (item.get("name") or ""):
            contains_miandian = True
    if contains_miandian and order_type != "纸箱":
        order_type = "综合（含棉）"
    product_parts = []
    for item in raw.get("items") or []:
        label = (item.get("spec") or "") or (item.get("name") or "")[:40]
        if label:
            product_parts.append(f"{label} x{item.get('qty', 0)}")
    ex = order_extra.get(oid, {})
    km_sid = resolve_km_sid(raw) or oid
    return {
        "inner_id": oid,
        "km_sid": km_sid,
        "tid": raw.get("tid") or raw.get("platform_tid") or "",
        "store": raw.get("shop_name") or "",
        "province": raw.get("receiver_province") or "",
        "city": raw.get("receiver_city") or "",
        "specs": specs,
        "product": "; ".join(product_parts[:3]) or "?",
        "seller_memo": raw.get("seller_memo") or "",
        "buyer_memo": raw.get("buyer_memo") or "",
        "qty": sum(i.get("qty", 0) for i in (raw.get("items") or [])),
        "type": order_type,
        "status": raw.get("order_status") or raw.get("status") or "",
        "status_label": raw.get("status_label") or "",
        "urgent": bool(ex.get("urgent")),
        "flow": flow,
    }


def apply_scan_report(
    db_config: dict,
    process_tree: list,
    order_id: str,
    step_name: str,
    worker: str,
    cache_file: str,
    extra_fields: dict | None = None,
) -> dict[str, Any]:
    ensure_scan_logs_table(db_config)
    orders = load_cache_orders(cache_file)
    o = find_order_in_cache(orders, order_id)
    if not o:
        return {"success": False, "msg": f"未找到订单 {order_id}"}

    # 退款拦截
    rs = str(o.get("refund_status") or "").strip()
    if rs and rs != "无":
        detail = str(o.get("refund_detail") or "").strip()
        reason = detail if detail else f"订单已{rs}"
        return {"success": False, "msg": f"订单 {order_id} 已退款，无法报工（{reason}）"}

    oid = internal_order_id(o)
    order_type = infer_order_type(o)
    steps = get_or_create_flow_steps(db_config, process_tree, oid, order_type)
    target = None
    for s in steps:
        if s["step"] == step_name:
            target = s
            break
    if not target:
        nxt = next((s for s in steps if not s.get("done")), None)
        return {
            "success": False,
            "msg": f"工序「{step_name}」不存在，下一道：{nxt['step'] if nxt else '无'}",
        }
    if target.get("done"):
        return {"success": False, "msg": f"工序「{step_name}」已完成"}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target["done"] = True
    target["time"] = now
    target["person"] = worker
    save_flow_row(db_config, oid, order_type, steps)

    # 校验额外字段
    step_fields = get_step_fields(process_tree, step_name)
    extra_json = ""
    if step_fields:
        extra_fields = extra_fields or {}
        clean = {}
        for fdef in step_fields:
            key = fdef.get("key", "")
            val = extra_fields.get(key, "")
            if fdef.get("required") and not val:
                return {"success": False, "msg": f"字段「{fdef.get('label', key)}」不能为空"}
            ftype = fdef.get("type", "text")
            if ftype == "number" and val:
                try:
                    val = float(val)
                    if val == int(val):
                        val = int(val)
                except (ValueError, TypeError):
                    return {"success": False, "msg": f"字段「{fdef.get('label', key)}」必须是数字"}
            clean[key] = val
        extra_json = json.dumps(clean, ensure_ascii=False)

    try:
        db = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
        cur = db.cursor()
        cur.execute(
            """
            INSERT INTO scan_logs (order_id, step_name, worker, status, extra_data)
            VALUES (%s,%s,%s,'已完成',%s)
            """,
            (oid, step_name, worker, extra_json or None),
        )
        db.commit()
        cur.close()
        db.close()
    except Exception as e:
        return {"success": False, "msg": f"写入报工记录失败: {e}"}
    all_done = all(s.get("done") for s in steps)
    return {
        "success": True,
        "order_id": oid,
        "step": step_name,
        "worker": worker,
        "time": now,
        "all_done": all_done,
        "flow": steps,
    }


def fetch_scan_logs(db_config: dict, limit: int = 50) -> list[dict]:
    ensure_scan_logs_table(db_config)
    try:
        db = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
        cur = db.cursor()
        cur.execute(
            """
            SELECT order_id, step_name, worker, status, extra_data, created_at
            FROM scan_logs ORDER BY id DESC LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        cur.close()
        db.close()
        logs = []
        for r in rows:
            t = r.get("created_at")
            if isinstance(t, datetime):
                t = t.strftime("%H:%M")
            logs.append(
                {
                    "time": str(t or ""),
                    "order_id": r.get("order_id") or "",
                    "step": r.get("step_name") or "",
                    "worker": r.get("worker") or "",
                    "status": "✅" if (r.get("status") or "") == "已完成" else r.get("status"),
                    "extra_data": r.get("extra_data") or "",
                }
            )
        return logs
    except Exception as e:
        print(f"[scan_logs] 读取失败: {e}")
        return []


def build_daily_report(
    cache_file: str,
    db_config: dict,
    report_date: str,
    order_extra: dict,
    employee_status: dict,
) -> dict[str, Any]:
    orders = load_cache_orders(cache_file)
    day_orders = [o for o in orders if order_on_date(o, report_date)]
    ensure_scan_logs_table(db_config)
    logs_today = []
    try:
        db = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
        cur = db.cursor()
        cur.execute(
            """
            SELECT order_id, step_name, worker, created_at
            FROM scan_logs WHERE DATE(created_at)=%s ORDER BY id DESC
            """,
            (report_date,),
        )
        logs_today = cur.fetchall()
        cur.close()
        db.close()
    except Exception as e:
        print(f"[daily_report] scan_logs: {e}")

    total_qty = 0
    for o in day_orders:
        total_qty += sum(int(i.get("qty") or 0) for i in (o.get("items") or []))

    yesterday = (datetime.strptime(report_date, "%Y-%m-%d").date() - timedelta(days=1)).isoformat()
    y_orders = [o for o in orders if order_on_date(o, yesterday)]
    y_qty = sum(sum(int(i.get("qty") or 0) for i in (o.get("items") or [])) for o in y_orders)

    def pct_change(today_v: float, y_v: float) -> str:
        if y_v <= 0:
            return "—"
        ch = (today_v - y_v) / y_v * 100
        return f"{ch:+.1f}%"

    step_counts: dict[str, int] = defaultdict(int)
    worker_counts: dict[str, int] = defaultdict(int)
    for row in logs_today:
        step_counts[row.get("step_name") or "—"] += 1
        w = (row.get("worker") or "").strip()
        if w:
            worker_counts[w] += 1

    production_lines = [
        {"line": k, "output": v, "status": "正常"}
        for k, v in sorted(step_counts.items(), key=lambda x: -x[1])[:8]
    ]
    if not production_lines:
        production_lines = [{"line": "暂无报工", "output": 0, "status": "—"}]

    done_orders = []
    for row in logs_today[:20]:
        oid = row.get("order_id") or ""
        o = find_order_in_cache(orders, oid)
        prod = "—"
        qty = 0
        if o:
            items = o.get("items") or []
            if items:
                prod = (items[0].get("spec") or items[0].get("name") or "?")[:40]
            qty = sum(int(i.get("qty") or 0) for i in items)
        t = row.get("created_at")
        if isinstance(t, datetime):
            t = t.strftime("%H:%M")
        done_orders.append(
            {
                "id": oid,
                "product": prod,
                "qty": qty,
                "last_step": row.get("step_name") or "",
                "done_time": str(t or ""),
            }
        )

    worker_stats = [
        {
            "name": name,
            "position": "报工",
            "group": "生产",
            "count": cnt,
            "steps": str(cnt),
            "status": employee_status.get(name, "出勤"),
        }
        for name, cnt in sorted(worker_counts.items(), key=lambda x: -x[1])[:30]
    ]

    completed_flows = 0
    try:
        db = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM production_flows WHERE status='done'")
        completed_flows = int((cur.fetchone() or {}).get("c") or 0)
        cur.close()
        db.close()
    except Exception:
        pass

    return {
        "date": report_date,
        "summary": {
            "total_orders": len(day_orders),
            "completed_orders": completed_flows,
            "output_qty": total_qty,
            "defect_rate": "—",
        },
        "comparison": [
            {
                "name": "当日订单",
                "today": str(len(day_orders)),
                "yesterday": str(len(y_orders)),
                "change": pct_change(len(day_orders), len(y_orders)),
            },
            {
                "name": "当日件数",
                "today": str(total_qty),
                "yesterday": str(y_qty),
                "change": pct_change(total_qty, y_qty),
            },
            {
                "name": "报工次数",
                "today": str(len(logs_today)),
                "yesterday": "—",
                "change": "—",
            },
        ],
        "production_lines": production_lines,
        "done_orders": done_orders,
        "worker_stats": worker_stats,
    }


def build_databoard(
    cache_file: str,
    range_type: str,
    order_extra: dict,
) -> dict[str, Any]:
    now = datetime.now()
    orders = load_cache_orders(cache_file)
    in_range = filter_orders_by_range(orders, range_type)
    if range_type == "live":
        days_span = 1
    elif range_type == "yesterday":
        days_span = 1
    elif range_type == "week":
        days_span = max(1, now.date().weekday() + 1)
    elif range_type == "month":
        days_span = now.day
    elif range_type == "last30":
        days_span = 30
    elif range_type == "quarter":
        qm = ((now.month - 1) // 3) * 3 + 1
        days_span = max(1, (now.date() - date(now.year, qm, 1)).days + 1)
    else:
        days_span = 7

    try:
        import km_api as _km

        amt = _km.km_to_float
    except ImportError:

        def amt(v, default=0.0):
            try:
                return float(v or 0)
            except (TypeError, ValueError):
                return default

    total_amount = sum(amt(o.get("total_amount")) for o in in_range)
    store_counts: dict[str, int] = defaultdict(int)
    platform_counts: dict[str, int] = defaultdict(int)
    step_load: dict[str, int] = defaultdict(int)
    for o in in_range:
        store_counts[(o.get("shop_name") or "未知").strip() or "未知"] += 1
        plat = (o.get("platform_label") or o.get("platform") or "其他").strip()
        platform_counts[plat] += 1

    trend = []
    for i in range(min(14, days_span) - 1, -1, -1):
        d = (now - timedelta(days=i)).date()
        ds = d.strftime("%Y-%m-%d")
        cnt = sum(1 for o in in_range if order_on_date(o, ds))
        trend.append({"date": d.strftime("%m-%d"), "output": cnt, "orders": cnt})

    total_o = len(in_range) or 1
    store_distribution = [
        {"name": n, "count": c, "pct": round(c * 100 / total_o)}
        for n, c in sorted(store_counts.items(), key=lambda x: -x[1])[:10]
    ]
    platform_distribution = [
        {"name": n, "count": c, "pct": round(c * 100 / total_o)}
        for n, c in sorted(platform_counts.items(), key=lambda x: -x[1])
    ]
    urgent_n = sum(
        1
        for o in in_range
        if order_extra.get(internal_order_id(o), {}).get("urgent")
    )

    hourly = [{"hour": f"{h:02}", "val": 0} for h in range(8, 21)]
    for o in in_range:
        raw = str(o.get("pay_time") or o.get("created") or "")
        digits = "".join(c for c in raw if c.isdigit())
        if len(digits) >= 10:
            try:
                h = int(digits[8:10])
                if 8 <= h <= 20:
                    hourly[h - 8]["val"] += 1
            except ValueError:
                pass

    return {
        "stats": {
            "total_output": int(round(total_amount)),
            "total_orders": len(in_range),
            "completed": 0,
            "in_production": len(in_range),
            "avg_daily": round(len(in_range) / days_span, 1),
            "on_time_rate": "—",
            "defect_rate": "—",
            "urgent_count": urgent_n,
        },
        "trend": trend or [{"date": now.strftime("%m-%d"), "output": 0}],
        "store_distribution": store_distribution,
        "platform_distribution": platform_distribution,
        "process_load": [
            {
                "name": d["name"],
                "current": d["count"],
                "capacity": total_o,
                "pct": d["pct"],
            }
            for d in platform_distribution
        ],
        "product_type": store_distribution[:5],
        "hourly_output": hourly,
        "worker_productivity": [],
        "recent_news": [
            {
                "icon": "📦",
                "text": f"{(o.get('shop_name') or '')} #{internal_order_id(o)}",
                "time": (o.get("created") or "")[-8:],
            }
            for o in sorted(
                in_range,
                key=lambda x: str(x.get("created") or ""),
                reverse=True,
            )[:8]
        ],
    }
