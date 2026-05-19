# -*- coding: utf-8 -*-
"""
订单同步：快麦 erp.trade.outstock.simple.query（全平台待发货）+ 1688 开放平台直连兜底。
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
    - 快麦 erp.trade.outstock.simple.query（全平台，source_filter=None）
    - 可选：1688 开放平台直连补充（有 alibaba_shops.json 时）
    """
    cache_path = Path(cache_file)
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
            _flush_cache_snapshot(cache_path, merged, report, shops, partial=True)
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

        _set_sync_phase("done", "写入缓存")
        n_pending = _flush_cache_snapshot(cache_path, merged, report, shops, partial=False)
        report["pending_count"] = n_pending
        by_src = report.get("km_outstock_by_source") or {}
        print(
            f"[订单同步] 完成: 待发货 {n_pending} 条 "
            f"(快麦outstock={report['km_outstock_count']} 按source={by_src} "
            f"1688直连={report['direct_1688_count']})"
        )
        return report


def read_realtime_cache_payload(
    cache_file: str | Path,
    shop_config: list | None = None,
) -> dict[str, Any]:
    """
    毫秒级读 orders_cache.json，供 /api/realtime/orders 使用。
    文件存在即返回（orders 可为空），不触发同步、不阻塞。
    """
    cache_path = Path(cache_file)
    cfg = shop_config if shop_config is not None else []

    if not cache_path.is_file():
        return {
            "success": True,
            "total": 0,
            "orders": [],
            "platforms": [],
            "shop_config": cfg,
            "cache_status": "missing",
            "report": {},
            "updated_at": None,
        }

    try:
        with cache_path.open("r", encoding="utf-8") as f:
            cache = json.load(f)
    except Exception as e:
        print(f"[实时订单] 读缓存失败: {e}")
        return {
            "success": True,
            "total": 0,
            "orders": [],
            "platforms": [],
            "shop_config": cfg,
            "cache_status": "error",
            "report": {},
            "updated_at": None,
        }

    cached_orders = list(cache.get("orders") or [])
    report = cache.get("report") or {}
    try:
        import km_api as _km

        for o in cached_orders:
            o["shop_name"] = normalize_shop_display(o.get("shop_name", ""))
            try:
                _km.finalize_cache_order(o)
            except Exception:
                pass
    except ImportError:
        for o in cached_orders:
            o["shop_name"] = normalize_shop_display(o.get("shop_name", ""))

    cached_orders.sort(key=lambda x: x.get("created", ""), reverse=True)
    status = "hit" if cached_orders else "empty"
    return {
        "success": True,
        "total": len(cached_orders),
        "orders": cached_orders,
        "platforms": list({o.get("platform", "1688") for o in cached_orders}),
        "shop_config": cfg,
        "cache_status": status,
        "report": report,
        "updated_at": cache.get("updated_at"),
    }


def _parse_item_display(spec: str, name: str, qty: int) -> str:
    """列表展示用：仅 SKU 规格，无规格时不回退商品标题。"""
    del name, qty  # 保留参数兼容旧调用
    return (spec or "").strip()


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
        return {
            "running": bool(_force_sync_state["running"]),
            "error": _force_sync_state["error"],
            "last": _force_sync_state["last"],
            "started_at": _force_sync_state["started_at"],
            "finished_at": _force_sync_state["finished_at"],
            "phase": _force_sync_state.get("phase") or "",
            "detail": _force_sync_state.get("detail") or "",
        }


def _flush_cache_snapshot(
    cache_path: Path,
    merged: dict[str, dict],
    report: dict[str, Any],
    shops: dict[str, dict],
    *,
    partial: bool = False,
) -> int:
    """分阶段写入缓存，避免长时间拉单时页面一直读旧数据。"""
    pending = [o for o in merged.values() if _is_pending_cache_order(o)]
    for o in pending:
        if "items" in o:
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
                        it["display"] = _parse_item_display(
                            it.get("spec", ""),
                            "",
                            it.get("qty", 0),
                        )
    report["pending_count"] = len(pending)
    payload = {
        "orders": pending,
        "updated_at": time.time(),
        "source": "kuaimai+1688",
        "shop_count": len(shops),
        "report": dict(report),
        "partial": partial,
    }
    cache_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return len(pending)


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
                if not _force_sync_state.get("phase"):
                    _force_sync_state["phase"] = "idle"

    threading.Thread(target=_run, daemon=True).start()
    return True, "同步已开始，请稍候刷新列表"
