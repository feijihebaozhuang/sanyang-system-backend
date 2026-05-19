# -*- coding: utf-8 -*-
"""打印快麦子单原始 platformSpec / skuPropertiesName（排查 28272 等缺宽问题）。"""
from __future__ import annotations

import argparse
import json
import sys
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


def _find_line(trade: dict, needle: str) -> dict | None:
    for it in trade.get("orders") or trade.get("orderList") or []:
        if not isinstance(it, dict):
            continue
        blob = json.dumps(it, ensure_ascii=False)
        if needle in blob:
            return it
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="快麦子单规格字段探测")
    parser.add_argument("--sid", default="", help="快麦系统单号/内部单号片段")
    parser.add_argument("--tid", default="", help="平台 tid")
    parser.add_argument("--days", type=int, default=7, help="回溯天数")
    args = parser.parse_args()
    needle = (args.sid or args.tid or "").strip()
    if not needle:
        print("请指定 --sid 或 --tid，例如 --sid 28272", file=sys.stderr)
        return 2
    if not km_api.km_configured():
        print("未配置 KM_* 或 km_token.json", file=sys.stderr)
        return 2

    km_api.km_ensure_session()
    orders, errors = km_api.km_fetch_trades(days_back=args.days, time_type="pay_time")
    if errors:
        print("拉单告警:", json.dumps(errors[:3], ensure_ascii=False), file=sys.stderr)
    hit = None
    line = None
    for tr in orders:
        sid = str(tr.get("sid") or tr.get("soId") or "")
        tid = str(tr.get("tid") or "")
        if needle not in sid and needle not in tid:
            continue
        line = _find_line(tr, needle) or (tr.get("orders") or [None])[0]
        hit = tr
        break
    if not hit or not line:
        print(f"未找到含 {needle!r} 的订单（共扫描 {len(orders)} 条）")
        return 1

    snap = km_api.km_item_snapshot(line)
    merged = km_api.km_item_for_resolve({**snap, "_km": snap})
    out = {
        "sid": hit.get("sid"),
        "tid": hit.get("tid"),
        "title": line.get("title") or line.get("sysTitle"),
        "platformSpec_raw": line.get("platformSpec"),
        "platformSpec_parsed": km_api.km_platform_spec_json_to_attrs(line.get("platformSpec")),
        "skuPropertiesName": line.get("skuPropertiesName"),
        "collect_attrs": km_api.km_collect_item_raw_attrs(merged),
        "display": km_api.km_resolve_item_display(merged),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
