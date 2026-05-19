#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 index_production.html 重建 UTF-8 正常的 index.html。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROD = ROOT / "index_production.html"
CS = ROOT / "index_cs.html"
OUT = ROOT / "index.html"

PROD_EXTRA_CSS = """
        /* 打单分页 / 手机卡片 / WPS 嵌入 */
        #page-production .prod-cards-mobile { display: none; }
        #page-production .prod-pager-wrap { display: none; margin: 8px 0; }
        .prod-pager { display: flex; align-items: center; gap: 10px; padding: 10px 0; flex-wrap: wrap; }
        .prod-pager button { padding: 6px 12px; border: 1px solid #d9d9d9; background: #fff; border-radius: 4px; cursor: pointer; }
        .prod-pager button:disabled { opacity: 0.4; cursor: not-allowed; }
        .prod-cards-mobile { display: none; padding: 0 0 8px; }
        .prod-card {
            width: 100%; max-width: 100%; background: #fff; border: 1px solid #e8e8e8;
            border-radius: 8px; padding: 10px; margin-bottom: 10px; box-sizing: border-box;
        }
        .wps-embed-wrap {
            width: 100%; height: calc(100vh - 140px); background: #fff;
            border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }
        .wps-embed-wrap iframe { width: 100%; height: 100%; border: none; }
"""

PROD_MOBILE_CSS = """
            #page-production .prod-table-desktop { display: none; }
            #page-production .prod-cards-mobile { display: block !important; }
            #page-production .prod-pager-wrap { display: block !important; margin: 8px 0; }
            .prod-pager { flex-wrap: wrap; justify-content: center; gap: 8px; font-size: 12px; }
            .wps-embed-wrap { height: calc(100vh - 120px); min-height: 400px; }
"""

ANNOUNCEMENT_BAR = """
        <motion.div id="prodAnnouncementBar" style="display:none;margin:12px 0;background:#fff7e6;border:1px solid #ffd591;border-radius:10px;padding:12px 14px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap;">
                <div style="flex:1;min-width:200px;">
                    <div style="font-size:14px;font-weight:600;color:#d48806;margin-bottom:6px;">📢 <span id="prodAnnTitle">公告</span> <span id="prodAnnBadge" style="display:none;background:#e94560;color:#fff;font-size:11px;padding:1px 6px;border-radius:10px;margin-left:6px;">未读</span></div>
                    <div id="prodAnnContent" style="font-size:13px;color:#333;line-height:1.6;white-space:pre-wrap;"></div>
                </div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;">
                    <button type="button" id="prodAnnReadBtn" onclick="markAnnouncementRead()" style="padding:6px 12px;background:#1677ff;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px;">标为已读</button>
                    <button type="button" id="prodAnnEditBtn" onclick="openAnnouncementEditor()" style="display:none;padding:6px 12px;background:#52c41a;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px;">编辑公告</button>
                </div>
            </div>
        </motion.div>
""".replace("<motion.div", "<div").replace("</motion.div>", "</div>")

WPS_PAGE = """
    <!-- ===== WPS 刀模表（点击底部入口后再加载） ===== -->
    <div id="page-wps-kdocs" class="page-section">
        <div class="overview-header">
            <h3>📄 WPS 刀模表</h3>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <a href="https://www.kdocs.cn/l/cdIlitRGKpMw" target="_blank" rel="noopener" style="padding:6px 14px;background:#1677ff;color:#fff;border-radius:6px;text-decoration:none;font-size:13px;">新窗口打开</a>
                <button type="button" onclick="switchTopPage('dimoldb', document.querySelector('#topNav a[onclick*=dimoldb]'))" style="padding:6px 14px;background:#f5f5f5;border:1px solid #ddd;border-radius:6px;cursor:pointer;font-size:13px;">固定刀模库</button>
            </div>
        </div>
        <div class="wps-embed-wrap">
            <iframe id="wpsKdocsFrame" title="WPS刀模" src="about:blank" data-src="https://www.kdocs.cn/l/cdIlitRGKpMw"></iframe>
        </div>
        <p style="font-size:12px;color:#888;margin-top:8px;">首次进入本页后加载文档；若无法显示请点「新窗口打开」。</p>
    </div>
"""

BATCH_CALC_FN = """
async function batchCalcMaterialOrders() {
    const ids = getSelectedProdIds();
    if (!ids.length) { alert('请先勾选要打单的订单'); return; }
    if (typeof window.batchCalcMaterialOrdersImpl === 'function') {
        return window.batchCalcMaterialOrdersImpl(ids);
    }
    alert('算料模块未加载，请刷新页面');
}
"""


def extract_js_function(text: str, signature: str) -> str:
    idx = text.index(signature)
    i = idx
    depth = 0
    started = False
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
            started = True
        elif c == "}":
            depth -= 1
            if started and depth == 0:
                return text[idx : i + 1]
        i += 1
    raise ValueError(f"unclosed function: {signature!r}")


def replace_js_function(text: str, signature: str, new_body: str) -> str:
    old = extract_js_function(text, signature)
    return text.replace(old, new_body, 1)


def main() -> None:
    text = PROD.read_text(encoding="utf-8")
    cs = CS.read_text(encoding="utf-8")

    text = text.replace(
        "        /* ===== 登录页 ===== */",
        PROD_EXTRA_CSS + "\n        /* ===== 登录页 ===== */",
        1,
    )
    text = text.replace(
        "            /* 报价 */\n            #page-quote .quote-layout { grid-template-columns: 1fr !important; }\n        }",
        "            /* 报价 */\n            #page-quote .quote-layout { grid-template-columns: 1fr !important; }"
        + PROD_MOBILE_CSS
        + "\n        }",
        1,
    )

    text = text.replace(
        "        </div>\n\n        <!-- 刀模快速查询 -->",
        "        </div>\n" + ANNOUNCEMENT_BAR + "\n        <!-- 刀模快速查询 -->",
        1,
    )

    text = text.replace(
        '    <div class="order-table-wrap">\n        <table>\n            <thead><tr>\n                <th style="width:36px;"><input type="checkbox" onchange="toggleAllProdCheckbox(this)"></th>',
        '    <motion.div class="order-table-wrap prod-table-desktop">\n        <table>\n            <thead><tr>\n                <th style="width:36px;"><input type="checkbox" onchange="toggleAllProdCheckbox(this)"></th>'.replace(
            "<motion.div", "<div"
        ),
        1,
    )
    text = text.replace(
        '            <tbody id="prodTable"></tbody>\n        </table>\n    </div>\n</div>\n\n    <!-- ===== 扫码报工页 ===== -->',
        '            <tbody id="prodTable"></tbody>\n        </table>\n    </div>\n    <div id="prodCardsMobile" class="prod-cards-mobile"></div>\n    <div id="prodPagination" class="prod-pager-wrap"></div>\n</div>\n\n    <!-- ===== 扫码报工页 ===== -->',
        1,
    )
    text = text.replace(
        '<button onclick="batchInitFlows()" style="padding:4px 12px;background:#fa8c16;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">📋 创建工单</button>',
        '<button onclick="batchInitFlows()" style="padding:4px 12px;background:#fa8c16;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">📋 创建工单</button>\n            <button onclick="batchCalcMaterialOrders()" style="padding:4px 12px;background:#722ed1;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">📐 批量算料</button>',
        1,
    )

    text = text.replace(
        "    <!-- ===== 扫码报工页 ===== -->",
        WPS_PAGE + "\n    <!-- ===== 扫码报工页 ===== -->",
        1,
    )

    text = text.replace(
        """    <div class="footer-card" onclick="switchSubPage('dimoldb', null)" data-perm="刀模库">
        <div class="icon">🔩</div>
        <div class="f-title">WPS刀模嵌入</div>
        <div class="f-desc">查看和管理固定刀模</div>
    </div>""",
        """    <div class="footer-card" onclick="openWpsKdocsEmbed()" data-perm="刀模库">
        <div class="icon">🔩</div>
        <div class="f-title">WPS刀模嵌入</div>
        <div class="f-desc">查看和管理固定刀模（点击进入后加载）</div>
    </div>""",
        1,
    )

    text = text.replace(
        '<script src="/static/auth_session.js"></script>',
        '<script src="/static/auth_session.js?v=20260520"></script>',
        1,
    )
    text = text.replace(
        "        try {\n            const res = await SY_AUTH.apiFetch('/api/login', {",
        "        try {\n            if (typeof globalThis.SY_AUTH === 'undefined') {\n                throw new Error('auth_session.js 未加载，请检查 /static/auth_session.js 是否返回 200');\n            }\n            const res = await SY_AUTH.apiFetch('/api/login', {",
        1,
    )
    text = text.replace(
        "        if (name === 'production') {\n            loadProdDashboard();\n        }",
        "        if (name === 'production') {\n            loadProdDashboard();\n            if (typeof loadProductionAnnouncements === 'function') loadProductionAnnouncements();\n        }",
        1,
    )

    start = cs.index("    /** 与 dimoldb_store.infer_inner_outer 一致 */")
    end = cs.index("    // ===== 固定刀模库 =====", start)
    dm_helpers = cs[start:end]
    mark = "    // ===== 固定刀模库 ====="
    text = text.replace(mark, dm_helpers + mark, 1)

    for sig in (
        "    async function quickSearchDimoldb()",
        "    async function homeQuickSearchDimoldb()",
    ):
        text = replace_js_function(text, sig, extract_js_function(cs, sig))

    # 删除重复的 fillDimoldbQuick（全量列表版）
    bad_dup = extract_js_function(
        text,
        "    async function fillDimoldbQuick(id) {\n        try {\n            const res = await fetch('/api/dimoldb');",
    )
    text = text.replace(bad_dup, "", 1)

    text = text.replace(
        """                        <div style="font-weight:600;font-size:14px;">${item.name}</div>
                        <div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ 📍' + item.remark : ''}""",
        """                        <div style="font-weight:600;font-size:14px;">${item.code ? '<span style="color:#1677ff;margin-right:6px;">#' + item.code + '</span>' : ''}${item.name}</div>
                        <div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ <span style="color:#999;font-size:11px;" title="' + String(item.remark||'').replace(/"/g,'&quot;') + '">' + (String(item.remark||'').length>28?String(item.remark||'').slice(0,28)+'…':String(item.remark||'')) + '</span>' : ''}""",
        1,
    )
    text = text.replace(
        """    function _invInferDimoldbRowType(m) {
        var dt = (m.dim_type || '').trim();
        if (dt === 'inner' || dt === 'outer') return dt;
        var name = m.name || '';
        var rk = m.remark || '';
        if (name.indexOf('(内)') >= 0 || name.indexOf('内径') >= 0 || rk.indexOf('内') >= 0) return 'inner';
        if (name.indexOf('(外)') >= 0 || name.indexOf('外径') >= 0 || rk.indexOf('外') >= 0) return 'outer';
        return '';
    }""",
        "    function _invInferDimoldbRowType(m) { return _dmInferInnerOuter(m); }",
        1,
    )
    text = text.replace(
        "🔧${m.remark||''}</span>`).join('')",
        "🔧${_dmDimCode(m)}</span>`).join('')",
        1,
    )
    text = text.replace(
        "            const body = { product_type: ptype, name, length: l, width: w, height: h, remark, stock, type_class, opens };\n                url = '/api/dimoldb';",
        "            const body = { product_type: ptype, name, length: l, width: w, height: h, remark, stock, type_class, opens };\n            let url = '/api/dimoldb';",
        1,
    )

    text = text.replace("</script>\n\n</body>", BATCH_CALC_FN + "\n</script>\n\n</body>", 1)
    text = text.replace("</body>", '<script src="/static/prod_ui.js"></script>\n</body>', 1)

    OUT.write_text(text, encoding="utf-8", newline="\n")
    t = OUT.read_text(encoding="utf-8")
    cjk = sum(1 for c in t if "\u4e00" <= c <= "\u9fff")
    bad = t.count("\ufffd")
    print(f"wrote {OUT.name}: U+FFFD={bad} CJK={cjk} bytes={len(t.encode('utf-8'))}")
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
