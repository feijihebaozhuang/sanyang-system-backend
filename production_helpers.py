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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_order (order_id),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        db.commit()
        cur.close()
        db.close()
        _scan_table_ready = True
    except Exception as e:
        print(f"[scan_logs] 建表失败: {e}")


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


def internal_order_id(o: dict) -> str:
    """快麦内部单号优先使用 so_id。"""
    return str(o.get("so_id") or o.get("km_sid") or "").strip()


def load_cache_orders(cache_file: str, *, finalize: bool = True) -> list[dict]:
    if not os.path.exists(cache_file):
        return []
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            orders = list(json.load(f).get("orders") or [])
    except (OSError, json.JSONDecodeError):
        return []
    if finalize:
        try:
            import km_api as _km

            for o in orders:
                _km.finalize_cache_order(o)
        except ImportError:
            pass
    return orders


def infer_order_type(o: dict) -> str:
    first = (o.get("items") or [{}])[0]
    name = (first.get("name") or "") + (first.get("spec") or "")
    if "纸箱" in name:
        return "纸箱"
    if "扣底盒" in name or "双插盒" in name:
        return "扣底盒"
    if "现货" in name:
        return "现货"
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
) -> list[dict]:
    row = get_flow_row(db_config, order_id)
    if row:
        steps = parse_flow_steps(row.get("steps_json"))
        if steps:
            return steps
    dept = get_process_dept(process_tree, order_type)
    steps = steps_from_dept(dept)
    save_flow_row(db_config, order_id, order_type, steps)
    return steps


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
                "store": o.get("shop_name") or "",
                "province": o.get("receiver_province") or (parts[0] if parts else ""),
                "city": o.get("receiver_city") or (parts[1] if len(parts) > 1 else ""),
                "specs": specs,
                "product": "; ".join(product_parts[:3]) or "?",
                "seller_memo": o.get("seller_memo") or "",
                "buyer_memo": o.get("buyer_memo") or "",
                "qty": sum(i.get("qty", 0) for i in (o.get("items") or [])),
                "type": order_type,
                "urgent": bool(ex.get("urgent")),
                "flow": flow,
            }
        )
    return orders_data


def apply_scan_report(
    db_config: dict,
    process_tree: list,
    order_id: str,
    step_name: str,
    worker: str,
    cache_file: str,
) -> dict[str, Any]:
    ensure_scan_logs_table(db_config)
    orders = load_cache_orders(cache_file)
    o = find_order_in_cache(orders, order_id)
    if not o:
        return {"success": False, "msg": f"未找到订单 {order_id}"}
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
    try:
        db = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
        cur = db.cursor()
        cur.execute(
            """
            INSERT INTO scan_logs (order_id, step_name, worker, status)
            VALUES (%s,%s,%s,'已完成')
            """,
            (oid, step_name, worker),
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
            SELECT order_id, step_name, worker, status, created_at
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
