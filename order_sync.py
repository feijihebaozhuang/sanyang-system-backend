# -*- coding: utf-8 -*-
"""
订单同步：快麦（含 1688 店铺，无需奇门）+ 1688 开放平台直连兜底。
客服端 / 生产端共用。
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

import km_api

_sync_lock = threading.Lock()

# 1688 快麦简称 → shop_config 简称
SHOP_NAME_ALIAS = {
    "友尚包装": "友尚",
    "亚润包装": "亚润",
    "三羊包装": "三羊",
    "正方形包装": "正方形",
    "大鱼包装": "大鱼",
    "新鑫星包装": "新鑫星",
    "东莞市友尚包装有限公司": "友尚",
    "东莞市亚润包装制品有限公司": "亚润",
    "东莞市三羊包装制品有限公司": "三羊",
    "东莞市正方形包装制品有限公司": "正方形",
    "东莞市大鱼包装制品有限公司": "大鱼",
    "东莞市新鑫星包装纸品有限公司": "新鑫星",
}

KM_PENDING = frozenset(
    {
        "WAIT_SEND_GOODS",
        "WAIT_AUDIT",
        "WAIT_PACKAGE",
        "WAIT_WEIGHT",
        "WAIT_EXPRESS_PRINT",
        "WAIT_DEST_SEND_GOODS",
        "FINISHED_AUDIT",
    }
)


def normalize_shop_display(name: str) -> str:
    s = km_api.km_normalize_shop_name((name or "").strip())
    return SHOP_NAME_ALIAS.get(s, SHOP_NAME_ALIAS.get(name or "", s))


def _is_pending_cache_order(o: dict) -> bool:
    if o.get("platform") == "1688":
        st = o.get("order_status") or ""
        if st == "waitsellersend":
            return True
        if (o.get("sync_source") or "").startswith("1688"):
            return st in ("", "waitsellersend") or o.get("status_label") == "待发货"
    st = (o.get("order_status") or "").strip()
    return st in KM_PENDING or o.get("status_label") in ("待发货", "待审核", "待打包", "待打印")


def _dedupe_merge(existing: dict[str, dict], new_list: list[dict]) -> None:
    for o in new_list:
        if not o.get("so_id"):
            continue
        key = str(o["so_id"])
        prev = existing.get(key)
        if not prev:
            existing[key] = o
            continue
        # 1688 直连地址更全时优先
        if o.get("sync_source") == "1688_api" and o.get("receiver_address"):
            existing[key] = o
        elif prev.get("sync_source") != "1688_api" and o.get("items"):
            existing[key] = o


def sync_orders_to_cache(
    cache_file: str | Path,
    *,
    days_back: int = 30,
    memo_getter: Callable[[str], str] | None = None,
    include_1688_direct: bool = True,
) -> dict[str, Any]:
    """
    写入 orders_cache.json。
    - 淘系 tm/tb：快麦 erp.trade.outstock.simple.query（全账号，无需 userId）
    - 1688：快麦 erp.trade.list.query（单店 userId，无需奇门）
    - 1688：开放平台直连补充（有 alibaba_shops.json 时）
    - 其他平台：快麦 list.query 按店
    """
    cache_path = Path(cache_file)
    report: dict[str, Any] = {
        "km_count": 0,
        "km_outstock_count": 0,
        "km_1688_count": 0,
        "direct_1688_count": 0,
        "pending_count": 0,
        "errors": [],
    }

    with _sync_lock:
        merged: dict[str, dict] = {}
        shops: dict[str, dict] = {}

        if km_api.km_configured():
            km_api.km_ensure_session()
            shops = km_api.km_shop_lookup(refresh=True)
            ids_1688 = [u for u, s in shops.items() if s.get("source") == "1688"]
            ids_other = [
                u
                for u, s in shops.items()
                if s.get("source") not in ("1688",) and s.get("source") not in km_api.KM_TM_TB_SOURCES
            ]
            has_tm_tb = any(s.get("source") in km_api.KM_TM_TB_SOURCES for s in shops.values())

            if has_tm_tb:
                raw_out, err_out = km_api.km_fetch_trades_outstock(
                    days_back,
                    time_type="upd_time",
                    status=km_api.KM_PENDING_STATUSES,
                    source_filter=km_api.KM_TM_TB_SOURCES,
                )
                report["km_outstock_count"] = len(raw_out)
                if err_out:
                    report["errors"].extend(err_out[:10])
                for row in raw_out:
                    o = km_api.km_trade_to_cache_order(row, shops)
                    o["shop_name"] = normalize_shop_display(o.get("shop_name") or "")
                    o["sync_source"] = "kuaimai_outstock"
                    _dedupe_merge(merged, [o])

            if ids_1688:
                raw_1688, err_1688 = km_api.km_fetch_trades(
                    days_back,
                    time_type="pay_time",
                    status=None,
                    shop_user_ids=ids_1688,
                )
                report["km_1688_count"] = len(raw_1688)
                if err_1688:
                    report["errors"].extend(err_1688[:10])
                for row in raw_1688:
                    o = km_api.km_trade_to_cache_order(row, shops)
                    o["shop_name"] = normalize_shop_display(o.get("shop_name") or "")
                    o["sync_source"] = "kuaimai_1688"
                    _dedupe_merge(merged, [o])

            if ids_other:
                raw_other, err_other = km_api.km_fetch_trades(
                    days_back,
                    time_type="pay_time",
                    status=km_api.KM_PENDING_STATUSES,
                    shop_user_ids=ids_other,
                )
                report["km_count"] = len(raw_other)
                if err_other:
                    report["errors"].extend(err_other[:10])
                for row in raw_other:
                    o = km_api.km_trade_to_cache_order(row, shops)
                    o["shop_name"] = normalize_shop_display(o.get("shop_name") or "")
                    o["sync_source"] = "kuaimai"
                    _dedupe_merge(merged, [o])
        else:
            report["errors"].append({"msg": "快麦未配置，跳过 KM 拉单"})

        if include_1688_direct:
            try:
                import alibaba_orders as ali

                if ali.alibaba_configured():
                    raw = ali.fetch_all_shops_orders()
                    direct_fmt = [
                        ali.format_order(o, memo_getter=memo_getter) for o in raw
                    ]
                    for o in direct_fmt:
                        full = o.get("shop_name") or ""
                        short = SHOP_NAME_ALIAS.get(full, full.replace("包装", ""))
                        o["shop_name"] = normalize_shop_display(short or full)
                    report["direct_1688_count"] = len(direct_fmt)
                    _dedupe_merge(merged, direct_fmt)
                else:
                    print("[订单同步] 未配置 ALIBABA_SHOPS，跳过 1688 直连")
            except Exception as e:
                report["errors"].append({"msg": f"1688直连异常: {e}"})
                print(f"[订单同步] 1688直连异常: {e}")

        pending = [o for o in merged.values() if _is_pending_cache_order(o)]
        report["pending_count"] = len(pending)

        for o in pending:
            if "items" in o:
                for it in o["items"]:
                    if isinstance(it, dict) and not it.get("display"):
                        spec = it.get("spec") or ""
                        name = it.get("name") or ""
                        qty = it.get("qty") or 0
                        it["display"] = _parse_item_display(spec, name, qty)

        payload = {
            "orders": pending,
            "updated_at": time.time(),
            "source": "kuaimai+1688",
            "shop_count": len(shops),
            "report": report,
        }
        cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(
            f"[订单同步] 完成: 待发货 {len(pending)} 条 "
            f"(淘系outstock={report['km_outstock_count']} 快麦1688={report['km_1688_count']} "
            f"快麦其他={report['km_count']} 1688直连={report['direct_1688_count']})"
        )
        return report


def _parse_item_display(spec: str, name: str, qty: int) -> str:
    """与 app_cs 展示逻辑一致的简易 display。"""
    parts = []
    if spec:
        parts.append(spec)
    if name and name not in spec:
        parts.append(name)
    if qty:
        parts.append(f"x{qty}")
    return " ".join(parts) if parts else name or ""


_force_sync_lock = threading.Lock()
_force_sync_state: dict[str, Any] = {
    "running": False,
    "error": None,
    "last": None,
    "started_at": None,
    "finished_at": None,
}


def force_sync_status() -> dict[str, Any]:
    with _force_sync_lock:
        return {
            "running": bool(_force_sync_state["running"]),
            "error": _force_sync_state["error"],
            "last": _force_sync_state["last"],
            "started_at": _force_sync_state["started_at"],
            "finished_at": _force_sync_state["finished_at"],
        }


def start_force_sync_async(
    cache_file: str | Path,
    *,
    days_back: int = 30,
    memo_getter: Callable | None = None,
    include_1688_direct: bool = True,
) -> tuple[bool, str]:
    """后台拉单，避免 Nginx/浏览器因同步过久返回 HTML 超时页。"""
    with _force_sync_lock:
        if _force_sync_state["running"]:
            return False, "同步正在进行中，请稍候"
        _force_sync_state["running"] = True
        _force_sync_state["error"] = None
        _force_sync_state["last"] = None
        _force_sync_state["started_at"] = time.time()
        _force_sync_state["finished_at"] = None

    def _run():
        try:
            report = sync_orders_to_cache(
                cache_file,
                days_back=days_back,
                memo_getter=memo_getter,
                include_1688_direct=include_1688_direct,
            )
            with _force_sync_lock:
                _force_sync_state["last"] = report
        except Exception as ex:
            with _force_sync_lock:
                _force_sync_state["error"] = str(ex)
            print(f"[订单同步] 手动同步失败: {ex}")
        finally:
            with _force_sync_lock:
                _force_sync_state["running"] = False
                _force_sync_state["finished_at"] = time.time()

    threading.Thread(target=_run, daemon=True).start()
    return True, "同步已开始，请稍候刷新列表"
