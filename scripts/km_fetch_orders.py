# -*- coding: utf-8 -*-
"""
快麦订单拉取脚本（服务器可直接运行）

推荐生产环境用页面「同步订单」或：
  curl -X POST .../api/sync/force  （后台线程 + 分阶段写缓存）

本脚本用途：
  --probe          连通性探测
  --sync-cache     与线上一致：order_sync 全量（outstock + list + 1688直连）
  --outstock-only  仅淘系 outstock（调试）
  --list-only      仅 erp.trade.list.query 按店

Token：km_token.json 或 KM_APP_KEY / KM_APP_SECRET / KM_SESSION
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env", override=False)
except ImportError:
    pass

import km_api  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="快麦订单拉取")
    parser.add_argument("--days", type=int, default=3, help="回溯天数")
    parser.add_argument("--probe", action="store_true", help="连通性探测")
    parser.add_argument(
        "--sync-cache",
        action="store_true",
        help="写入 orders_cache.json（与线上一致，分阶段落盘）",
    )
    parser.add_argument(
        "--cache-file",
        type=str,
        default="",
        help="缓存路径，默认项目根 orders_cache.json",
    )
    parser.add_argument("--outstock-only", action="store_true", help="仅淘系 outstock")
    parser.add_argument("--list-only", action="store_true", help="仅 list.query")
    parser.add_argument("--out", type=str, default="", help="探测结果写入 JSON")
    args = parser.parse_args()

    if not km_api.km_configured():
        print("未配置：km_token.json 或 KM_* 环境变量", file=sys.stderr)
        return 2

    km_api.km_ensure_session(force=False)
    if args.probe:
        print(json.dumps(km_api.km_probe(), ensure_ascii=False, indent=2))
        return 0

    if args.sync_cache:
        import order_sync as osync

        cache = Path(args.cache_file) if args.cache_file else _ROOT / "orders_cache.json"
        print(f"[sync-cache] 开始全量同步 → {cache}（无 HTTP 超时，请耐心等待）")
        t0 = time.time()
        report = osync.sync_orders_to_cache(
            cache,
            days_back=args.days,
            include_1688_direct=True,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"完成，耗时 {time.time() - t0:.1f}s，待发货 {report.get('pending_count', 0)} 条")
        return 0

    shops = km_api.km_shop_lookup(refresh=True)
    all_raw: list[dict] = []
    errors: list[dict] = []

    if not args.list_only:
        raw_o, err_o = km_api.km_fetch_trades_outstock(
            days_back=args.days,
            time_type="upd_time",
            status=km_api.KM_PENDING_STATUSES,
            source_filter=km_api.KM_TM_TB_SOURCES,
        )
        print(f"[outstock] 淘系: {len(raw_o)} 条, 告警 {len(err_o)}")
        all_raw.extend(raw_o)
        errors.extend(err_o)

    if not args.outstock_only:
        ids_1688 = [u for u, s in shops.items() if s.get("source") == "1688"]
        ids_other = [
            u
            for u, s in shops.items()
            if s.get("source") not in ("1688",)
            and s.get("source") not in km_api.KM_TM_TB_SOURCES
        ]
        print(f"[list] 1688 店 {len(ids_1688)} 个, 其他店 {len(ids_other)} 个")
        for label, ids in (("1688", ids_1688), ("other", ids_other)):
            if not ids:
                continue
            raw, err = km_api.km_fetch_trades(
                args.days,
                time_type="pay_time",
                status=km_api.KM_PENDING_STATUSES,
                shop_user_ids=ids,
            )
            print(f"[list] {label}: {len(raw)} 条, 告警 {len(err)}")
            all_raw.extend(raw)
            errors.extend(err)

    print(f"合计原始单: {len(all_raw)} 条")
    if errors:
        print("告警样例:", json.dumps(errors[:3], ensure_ascii=False))

    if args.out:
        rows = [km_api.km_trade_to_cache_order(r, shops) for r in all_raw[:500]]
        Path(args.out).write_text(
            json.dumps(
                {
                    "count_raw": len(all_raw),
                    "errors": errors[:20],
                    "sample": rows[:5],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"已写入 {args.out}")

    return 0 if all_raw or not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
