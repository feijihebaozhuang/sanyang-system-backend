# -*- coding: utf-8 -*-
"""
快麦订单拉取脚本（服务器可直接运行）

推荐生产环境用页面「同步订单」或：
  curl -X POST .../api/sync/force  （后台线程 + 分阶段写缓存）

本脚本用途：
  --probe          连通性探测
  --sync-cache     与线上一致：order_sync（outstock 全平台 + 可选 1688 直连）
  --no-1688-direct  sync-cache 时跳过 1688 开放平台直连

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
        help="写入 orders_cache.json（与线上一致）",
    )
    parser.add_argument(
        "--cache-file",
        type=str,
        default="",
        help="缓存路径，默认项目根 orders_cache.json",
    )
    parser.add_argument(
        "--no-1688-direct",
        action="store_true",
        help="sync-cache 时跳过 1688 开放平台直连",
    )
    parser.add_argument("--out", type=str, default="", help="探测/拉单结果写入 JSON")
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
            include_1688_direct=not args.no_1688_direct,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"完成，耗时 {time.time() - t0:.1f}s，待发货 {report.get('pending_count', 0)} 条")
        return 0

    shops = km_api.km_shop_lookup(refresh=True)
    raw_o, err_o = km_api.km_fetch_trades_outstock(
        days_back=args.days,
        time_type="upd_time",
        status=km_api.KM_PENDING_STATUSES,
        source_filter=None,
    )
    print(f"[outstock] 全平台: {len(raw_o)} 条, 告警 {len(err_o)}")
    by_src: dict[str, int] = {}
    for row in raw_o:
        src = (row.get("source") or "unknown").strip()
        by_src[src] = by_src.get(src, 0) + 1
    print(f"[outstock] 按 source: {by_src}")

    if args.out:
        rows = [km_api.km_trade_to_cache_order(r, shops) for r in raw_o[:500]]
        Path(args.out).write_text(
            json.dumps(
                {
                    "count_raw": len(raw_o),
                    "by_source": by_src,
                    "errors": err_o[:20],
                    "sample": rows[:5],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"已写入 {args.out}")

    return 0 if raw_o or not err_o else 1


if __name__ == "__main__":
    raise SystemExit(main())
