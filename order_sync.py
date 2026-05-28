# -*- coding: utf-8 -*-
"""
订单同步：快麦 erp.trade.outstock.simple.query（全平台待发货）。
写入 MySQL order_cache 表（不再写 orders_cache.json）。
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

import km_api
import order_cache_store as ocs

_sync_lock = threading.Lock()

SHOP_NAME_ALIAS = {
    "友尚包装": "友尚",
    "亚润包装": "亚润",
    "三羊包装": "三羊",
    "正方形包装": "正方形",
    "大鱼包装": "大鱼",
    "新鑫星包装": "新鑫星",
    "阿里友尚": "友尚",
    "阿里亚润": "亚润",
    "阿里三羊": "三羊",
    "阿里正方形": "正方形",
    "阿里大鱼": "大鱼",
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


def default_cache_path() -> Path:
    """兼容旧参数：仅用于后台线程签名，实际只写 MySQL。"""
    return Path(__file__).resolve().parent / "orders_cache.json"


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
    return st in KM_PENDING or o.get("status_label") in (
        "待发货",
        "待审核",
        "待打包",
        "待打印",
    )


def _dedupe_merge(existing: dict[str, dict], new_list: list[dict]) -> None:
    for o in new_list:
        if not o.get("so_id"):
            continue
        key = str(o["so_id"])
        prev = existing.get(key)
        if not prev:
            existing[key] = o
            continue
        if o.get("sync_source") == "1688_api" and o.get("receiver_address"):
            existing[key] = o
        elif prev.get("sync_source") != "1688_api" and o.get("items"):
            existing[key] = o


def _prepare_pending_items(pending: list[dict]) -> None:
    for o in pending:
        if "items" not in o:
            continue
        for it in o["items"]:
            if isinstance(it, dict) and not it.get("display"):
                try:
                    from km_api import km_item_for_resolve, km_resolve_item_display

                    d = km_resolve_item_display(km_item_for_resolve(it))
                    if d:
                        it["display"] = d
                        it["platform_attrs"] = d
                except ImportError:
                    pass
                if not it.get("display"):
                    it["display"] = (it.get("spec") or "").strip()


def _maybe_enrich_sku_map(report: dict[str, Any]) -> None:
    """订单同步后补全缺失商家编码（限流，不阻塞主流程）。"""
    if os.getenv("KM_SKU_ENRICH_AFTER_ORDER", "1") == "0":
        return
    try:
        import km_sku_sync as kss

        rep = kss.enrich_unknown_skus_from_orders()
        if rep.get("enriched"):
            report["km_sku_enriched"] = rep
            print(f"[订单同步] 补 SKU 映射 {rep.get('enriched')} 条")
    except Exception as ex:
        report.setdefault("errors", []).append({"msg": f"SKU 回填: {ex}"})


def _write_mysql_snapshot(
    merged: dict[str, dict],
    report: dict[str, Any],
    shops: dict[str, dict],
    *,
    partial: bool = False,
) -> int:
    pending = [o for o in merged.values() if _is_pending_cache_order(o)]
    _prepare_pending_items(pending)
    report["pending_count"] = len(pending)
    if not ocs.mysql_cache_available():
        report["errors"].append({"msg": "MySQL 不可用"})
        return 0
    allow_empty = (
        not partial
        and not pending
        and not (report.get("errors") or [])
        and (
            km_api.km_configured()
            or int(report.get("direct_1688_count") or 0) > 0
        )
    )
    ocs.write_orders_snapshot(
        pending,
        report=dict(report),
        shops_count=len(shops),
        source="kuaimai",
        partial=partial,
        allow_empty=allow_empty,
    )
    stats = ocs.compute_dashboard_stats(pending)
    ocs.write_stats_cache("dashboard_summary", stats)
    try:
        import production_dashboard_cache as _pdc

        _pdc.invalidate_dashboard_cache()
    except ImportError:
        pass
    _maybe_enrich_sku_map(report)
    return len(pending)


def sync_orders_to_cache(
    cache_file: str | Path | None = None,
    *,
    days_back: int = 30,
    memo_getter: Callable[[str], str] | None = None,
    include_1688_direct: bool = False,
) -> dict[str, Any]:
    del cache_file  # 仅 MySQL
    from order_sync_coordinator import order_sync_cluster_lock

    with order_sync_cluster_lock() as acquired:
        if not acquired:
            return {
                "skipped": True,
                "reason": "another_worker_syncing",
                "pending_count": ocs.order_count_mysql() if ocs.mysql_cache_available() else 0,
                "errors": [],
            }
        return _sync_orders_to_cache_impl(
            days_back=days_back,
            memo_getter=memo_getter,
            include_1688_direct=include_1688_direct,
        )


def _sync_orders_to_cache_impl(
    *,
    days_back: int = 30,
    memo_getter: Callable[[str], str] | None = None,
    include_1688_direct: bool = False,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "km_outstock_count": 0,
        "km_outstock_by_source": {},
        "direct_1688_count": 0,
        "pending_count": 0,
        "errors": [],
    }

    with _sync_lock:
        merged: dict[str, dict] = {}
        shops: dict[str, dict] = {}

        if km_api.km_configured():
            km_api.km_ensure_session()
            _set_sync_phase("shops", "拉取店铺列表")
            shops = km_api.km_shop_lookup(refresh=True)
            report["shop_count_km"] = len(shops)

            _set_sync_phase("outstock", f"近{days_back}天待发货（全平台）")
            raw_out, err_out = km_api.km_fetch_trades_outstock(
                days_back,
                time_type="upd_time",
                status=km_api.KM_PENDING_STATUSES,
                source_filter=None,
            )
            report["km_outstock_count"] = len(raw_out)
            if err_out:
                report["errors"].extend(err_out[:10])
            for row in raw_out:
                o = km_api.km_trade_to_cache_order(row, shops)
                o["shop_name"] = normalize_shop_display(o.get("shop_name") or "")
                o["sync_source"] = "kuaimai_outstock"
                src = (o.get("source") or row.get("source") or "unknown").strip()
                report["km_outstock_by_source"][src] = (
                    report["km_outstock_by_source"].get(src, 0) + 1
                )
                _dedupe_merge(merged, [o])
            _write_mysql_snapshot(merged, report, shops, partial=True)
        else:
            report["errors"].append({"msg": "快麦未配置，跳过 KM 拉单"})

        if include_1688_direct:
            _set_sync_phase("1688_direct", "开放平台直连")
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

        _set_sync_phase("done", "写入 MySQL")
        n_pending = _write_mysql_snapshot(merged, report, shops, partial=False)
        report["pending_count"] = n_pending

        try:
            import customer_order_store as co_store
            import km_co_order_sync as kcos

            co_rep = kcos.sync_pending_shipments(co_store=co_store)
            report["co_km_shipment"] = co_rep
        except Exception as ex:
            report["errors"].append({"msg": f"客户单快麦回写: {ex}"})
        print(
            f"[订单同步] 完成: 待发货 {n_pending} 条 "
            f"(快麦={report['km_outstock_count']})"
        )
        return report


def sync_orders_incremental(
    cache_file: str | Path | None = None,
    *,
    hours_back: int = 6,
    days_back: int | None = None,
    memo_getter: Callable[[str], str] | None = None,
    include_1688_direct: bool = False,
) -> dict[str, Any]:
    """
    增量：以快麦待发货为准刷新近 N 天；库内旧快麦单若本次未返回则剔除（已发货/关闭）。
    非快麦来源（1688 直连等）保留。
    """
    del cache_file
    if days_back is None:
        days_back = max(1, int(os.getenv("ORDER_SYNC_INCREMENTAL_DAYS", "14")))
    from order_sync_coordinator import order_sync_cluster_lock

    with order_sync_cluster_lock() as acquired:
        if not acquired:
            return {
                "mode": "incremental",
                "skipped": True,
                "reason": "another_worker_syncing",
                "pending_count": ocs.order_count_mysql() if ocs.mysql_cache_available() else 0,
                "errors": [],
            }
        return _sync_orders_incremental_impl(
            hours_back=hours_back,
            days_back=days_back,
            memo_getter=memo_getter,
            include_1688_direct=include_1688_direct,
        )


def _sync_orders_incremental_impl(
    *,
    hours_back: int,
    days_back: int,
    memo_getter: Callable[[str], str] | None = None,
    include_1688_direct: bool = False,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "mode": "incremental",
        "hours_back": hours_back,
        "days_back": days_back,
        "km_outstock_count": 0,
        "km_dropped_stale": 0,
        "pending_count": 0,
        "errors": [],
    }
    if not ocs.mysql_cache_available():
        report["errors"].append({"msg": "MySQL 不可用"})
        return report

    with _sync_lock:
        existing = ocs.read_orders_as_map(finalize=False)
        merged: dict[str, dict] = {}
        km_seen: set[str] = set()
        shops: dict[str, dict] = {}

        if km_api.km_configured():
            km_api.km_ensure_session()
            shops = km_api.km_shop_lookup(refresh=False)
            raw_out, err_out = km_api.km_fetch_trades_outstock(
                days_back,
                time_type="upd_time",
                status=km_api.KM_PENDING_STATUSES,
                source_filter=None,
            )
            report["km_outstock_count"] = len(raw_out)
            if err_out:
                report["errors"].extend(err_out[:5])
            for row in raw_out:
                o = km_api.km_trade_to_cache_order(row, shops)
                o["shop_name"] = normalize_shop_display(o.get("shop_name") or "")
                o["sync_source"] = "kuaimai_incremental"
                sid = str(o.get("so_id") or "").strip()
                if sid:
                    merged[sid] = o
                    km_seen.add(sid)

        for sid, o in existing.items():
            src = (o.get("sync_source") or "")
            if src.startswith("kuaimai"):
                continue
            if _is_pending_cache_order(o):
                merged.setdefault(sid, o)

        report["km_dropped_stale"] = sum(
            1
            for sid, o in existing.items()
            if (o.get("sync_source") or "").startswith("kuaimai") and sid not in km_seen
        )

        if include_1688_direct:
            try:
                import alibaba_orders as ali

                if ali.alibaba_configured():
                    raw = ali.fetch_all_shops_orders()
                    direct_fmt = [
                        ali.format_order(o, memo_getter=memo_getter) for o in raw
                    ]
                    for o in direct_fmt:
                        o["shop_name"] = normalize_shop_display(o.get("shop_name") or "")
                    _dedupe_merge(merged, direct_fmt)
            except Exception as e:
                report["errors"].append({"msg": str(e)})

        report["pending_count"] = _write_mysql_snapshot(merged, report, shops, partial=False)
        return report


def read_realtime_cache_payload(
    cache_file: str | Path | None = None,
    shop_config: list | None = None,
    *,
    trigger_background_sync: bool = True,
    memo_getter: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """毫秒级读 MySQL；可选触发后台增量同步（访问即同步）。"""
    del cache_file
    cfg = shop_config if shop_config is not None else []

    if trigger_background_sync:
        try:
            import order_visit_sync as ovs

            ovs.schedule_incremental_sync(memo_getter=memo_getter, force=False)
        except Exception as ex:
            print(f"[实时订单] 调度增量同步失败: {ex}")

    cached_orders, status, meta = ocs.load_orders_for_api(finalize=True)
    report = meta.get("report") or {}

    for o in cached_orders:
        o["shop_name"] = normalize_shop_display(o.get("shop_name", ""))

    cached_orders.sort(key=lambda x: x.get("created", ""), reverse=True)
    updated_at = meta.get("updated_at")
    ago = None
    if updated_at:
        ago = max(0, int(time.time() - float(updated_at)))

    visit_st = {}
    try:
        import order_visit_sync as ovs

        visit_st = ovs.visit_sync_status()
    except Exception:
        pass

    cache_status = (
        "waiting_sync"
        if status == "waiting_sync"
        else ("hit" if cached_orders else "empty")
    )

    return {
        "success": True,
        "total": len(cached_orders),
        "orders": cached_orders,
        "platforms": list({o.get("platform", "1688") for o in cached_orders}),
        "shop_config": cfg,
        "cache_status": cache_status,
        "report": report,
        "updated_at": updated_at,
        "updated_ago_sec": ago,
        "storage": "mysql",
        "sync_running": visit_st.get("running"),
        "visit_sync": visit_st,
    }


_force_sync_lock = threading.Lock()
_force_sync_state: dict[str, Any] = {
    "running": False,
    "error": None,
    "last": None,
    "started_at": None,
    "finished_at": None,
    "phase": "",
    "detail": "",
}


def _set_sync_phase(phase: str, detail: str = "") -> None:
    with _force_sync_lock:
        _force_sync_state["phase"] = phase
        _force_sync_state["detail"] = detail
    print(f"[订单同步] {phase} {detail}".strip())


def force_sync_status() -> dict[str, Any]:
    with _force_sync_lock:
        st = {
            "running": bool(_force_sync_state["running"]),
            "error": _force_sync_state["error"],
            "last": _force_sync_state["last"],
            "started_at": _force_sync_state["started_at"],
            "finished_at": _force_sync_state["finished_at"],
            "phase": _force_sync_state.get("phase") or "",
            "detail": _force_sync_state.get("detail") or "",
        }
    try:
        import order_visit_sync as ovs

        st["visit_sync"] = ovs.visit_sync_status()
    except Exception:
        pass
    return st


def start_force_sync_async(
    cache_file: str | Path | None = None,
    *,
    days_back: int = 30,
    memo_getter: Callable | None = None,
    include_1688_direct: bool = False,
) -> tuple[bool, str]:
    with _force_sync_lock:
        if _force_sync_state["running"]:
            return False, "同步正在进行中，请稍候"
        _force_sync_state["running"] = True
        _force_sync_state["error"] = None
        _force_sync_state["last"] = None
        _force_sync_state["started_at"] = time.time()
        _force_sync_state["finished_at"] = None
        _force_sync_state["phase"] = "start"
        _force_sync_state["detail"] = ""

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
