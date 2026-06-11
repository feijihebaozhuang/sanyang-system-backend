#!/usr/bin/env python3
"""刀模库前端 Bug 1-6 + WPS 不自动加载（index_cs.html / index.html）"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HELPER = """
    /** 与 dimoldb_store.infer_inner_outer 一致 */
    function _dmDimCode(m) {
        return String((m && (m.code || m.dim_code || m.km_mapping_code)) || '').trim() || '未编码';
    }
    function _dmInferInnerOuter(m) {
        if (!m) return '';
        var dt = String(m.dim_type || '').trim();
        if (dt === 'inner' || dt === 'outer') return dt;
        var blob = [m.production_spec, m.remark, m.name].filter(Boolean).join(' ');
        var name = m.name || '';
        if (blob.indexOf('内径') >= 0 || name.indexOf('(内)') >= 0 || name.indexOf('内径') >= 0) return 'inner';
        if (blob.indexOf('外径') >= 0 || name.indexOf('(外)') >= 0 || name.indexOf('外径') >= 0) return 'outer';
        return '';
    }
    function _dmInvDimMatch(dmDt, riDt) {
        if (!dmDt) return true;
        if (!riDt) return true;
        return dmDt === riDt;
    }
"""

MARKER = "    // ===== 固定刀模库 ====="


def insert_helpers(text: str) -> str:
    if "_dmInferInnerOuter" in text:
        return text
    if MARKER not in text:
        raise SystemExit("marker not found for helpers")
    return text.replace(MARKER, HELPER + MARKER, 1)


def patch_inv_infer(text: str) -> str:
    """统一 _invInferDimoldbRowType 使用 production_spec + remark"""
    old = """    function _invInferDimoldbRowType(m) {
        var dt = (m.dim_type || '').trim();
        if (dt === 'inner' || dt === 'outer') return dt;
        var name = m.name || '';
        var rk = m.remark || '';
        if (name.indexOf('(内)') >= 0 || name.indexOf('内径') >= 0 || rk.indexOf('内') >= 0) return 'inner';
        if (name.indexOf('(外)') >= 0 || name.indexOf('外径') >= 0 || rk.indexOf('外') >= 0) return 'outer';
        return '';
    }"""
    new = """    function _invInferDimoldbRowType(m) {
        return _dmInferInnerOuter(m);
    }"""
    if old in text:
        return text.replace(old, new, 1)
    if "return _dmInferInnerOuter(m)" in text:
        return text
    return text


def patch_dm_html_remark(text: str) -> str:
    patterns = [
        r"🔧\$\{m\.remark\|\|''\}",
        r"📍\$\{m\.remark\|\|''\}",
        r"ð??§\$\{m\.remark\|\|''\}",
    ]
    repl = "🔧${_dmDimCode(m)}"
    for p in patterns:
        text = re.sub(p, repl, text)
    text = text.replace("${m.remark||''}", "${_dmDimCode(m)}")
    return text


def patch_home_quick(text: str) -> str:
    """homeQuickSearchDimoldb: invByDim + _dmInferInnerOuter + dim_code 显示"""
    # invBySpec -> invByDim block (index.html style)
    text = re.sub(
        r"// 按 spec 分组库存.*?\n\s*const invBySpec = \{\};\s*\n\s*for \(const inv of invItems\) \{\s*\n\s*const spec = inv\.spec \|\| inv\.name \|\| '';\s*\n\s*if \(!invBySpec\[spec\]\) invBySpec\[spec\] = \[\];\s*\n\s*invBySpec\[spec\]\.push\(inv\);\s*\n\s*\}",
        """// 按 LxWxH 分组库存（与刀模尺寸键一致）
            const invByDim = {};
            for (const inv of invItems) {
                const dk = inv.length + 'x' + inv.width + 'x' + inv.height;
                if (!invByDim[dk]) invByDim[dk] = [];
                invByDim[dk].push(inv);
            }""",
        text,
        count=1,
        flags=re.DOTALL,
    )
    # invByDim version in index_cs - already has invByDim, skip

    text = re.sub(
        r"let dmDimType = '';\s*\n\s*if \(m\.name\.includes\('\(内\)'\)[^}]+\}\s*\n\s*let relatedInv = invBySpec\[specKey\] \|\| invBySpec\[m\.name\] \|\| \[\];",
        """let dmDimType = _dmInferInnerOuter(m);
                    let relatedInv = invByDim[specKey] || [];""",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"let dmDimType = '';\s*\n\s*if \(m\.name\.includes\('\(内\)'\)[^}]+\}\s*\n\s*let relatedInv = invByDim\[specKey\] \|\| \[\];",
        """let dmDimType = _dmInferInnerOuter(m);
                    let relatedInv = invByDim[specKey] || [];""",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"if \(dmDimType\) \{\s*\n\s*relatedInv = relatedInv\.filter\(ri => ri\.dim_type === dmDimType\);\s*\n\s*\}",
        "relatedInv = relatedInv.filter(ri => _dmInvDimMatch(dmDimType, ri.dim_type));",
        text,
    )
    text = re.sub(
        r"\+ '<span style=\"color:#1677ff;\">[^<]*' \+ \(m\.remark \|\| '[^']*'\) \+ '</span>'",
        "+ '<span style=\"color:#1677ff;\">编码 ' + _dmDimCode(m) + '</span>'",
        text,
        count=1,
    )
    return text


def patch_quote_dim_search(text: str) -> str:
    old = """                    const items = `${m.name} 📍${m.remark || ''}`;
                    // 找对应库存
                    let relInv = [];
                    // 判断刀模是内径还是外径：name里带(内)/内径 → inner，带(外)/外径 → outer
                    let dmInner = m.name.includes('(内)') || m.name.includes('内径') || m.name.includes('内');
                    let dmOuter = m.name.includes('(外)') || m.name.includes('外径') || m.name.includes('外');
                    let dmDimType = '';
                    if (dmInner && !dmOuter) dmDimType = 'inner';
                    else if (dmOuter && !dmInner) dmDimType = 'outer';
                    if (dmDimType) {
                        relInv = invItems.filter(x => x.dim_type === dmDimType);
                    } else {
                        relInv = invItems;
                    }"""
    new = """                    const items = `${m.name} · ${_dmDimCode(m)}`;
                    let relInv = [];
                    const dmDimType = _dmInferInnerOuter(m);
                    relInv = invItems.filter(x => _dmInvDimMatch(dmDimType, x.dim_type));"""
    return text.replace(old, new) if old in text else text


def patch_quick_search(text: str) -> str:
    text = re.sub(
        r"let mDim = '';\s*\n\s*if \(m\.name\.includes\('\(内\)'\)[^}]+\}",
        "const mDim = _dmInferInnerOuter(m);",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"const isInner = m\.remark && m\.remark\.includes\('内'\);\s*\n\s*const isOuter = m\.remark && m\.remark\.includes\('外'\);",
        "const mDimQ = _dmInferInnerOuter(m);\n                    const isInner = mDimQ === 'inner';\n                    const isOuter = mDimQ === 'outer';",
        text,
        count=1,
    )
    text = re.sub(
        r"\$\{m\.remark \? `<motion[^`]*\$\{m\.remark\}[^`]*` : ''\}",
        "${`<motion.div style=\"font-size:12px;color:#888;margin-top:4px;\">编码 ${_dmDimCode(m)}</motion.div>`}",
        text,
        count=1,
    )
    # simpler replace for remark line in quickSearch
    text = text.replace(
        "${m.remark ? `<motion.div style=\"font-size:13px;color:#e67e22;margin-top:4px;font-weight: bold;\">📍 ${m.remark}</motion.div>` : ''}",
        "${`<motion.div style=\"font-size:12px;color:#888;margin-top:4px;\">编码 ${_dmDimCode(m)}</motion.div>`}",
    )
    text = text.replace(
        "${m.remark ? `<motion.div style=\"font-size:13px;color:#e67e22;margin-top:4px;font-weight: bold;\">📍 ${m.remark}</motion.div>` : ''}",
        "",
    )
    # fix botched motion tags - use div only
    text = text.replace("<motion.div", "<div").replace("</motion.div>", "</motion.div>")
    return text


def patch_dimoldb_list(text: str) -> str:
    """列表主显示 code，remark 缩短"""
    old_cs = """                        <motion.div style="font-weight:600;font-size:14px;">${item.name}</motion.div>
                        <motion.div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ 📍' + item.remark : ''}"""
    # try without motion
    patterns = [
        (
            r'<motion.div style="font-weight:600;font-size:14px;">\$\{item\.name\}</motion.div>',
            '<motion.div style="font-weight:600;font-size:14px;">${item.code ? `<span style="color:#1677ff;margin-right:6px;">#${item.code}</span>` : ""}${item.name}</motion.div>',
        ),
    ]
    # index_cs plain html
    old1 = """                        <div style="font-weight:600;font-size:14px;">${item.name}</motion.div>
                        <div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ 📍' + item.remark : ''}"""
    new1 = """                        <div style="font-weight:600;font-size:14px;">${item.code ? '<span style="color:#1677ff;margin-right:6px;">#' + item.code + '</span>' : ''}${item.name}</motion.div>
                        <div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ <span style="color:#999;" title="' + (item.remark||'').replace(/"/g,'&quot;') + '">' + ((item.remark||'').length>24?(item.remark||'').slice(0,24)+'…':(item.remark||'')) + '</span>' : ''}"""
    if old1 in text:
        text = text.replace(old1, new1.replace("</motion.div>", "</motion.div>"))
    old1 = old1.replace("</motion.div>", "</motion.div>")
    new1 = new1.replace("</motion.div>", "</motion.div>")
    if "font-weight:600;font-size:14px;\">${item.name}</motion.div>" in text:
        pass
    # direct replace for index_cs
    cs_old = """                        <div style="font-weight:600;font-size:14px;">${item.name}</motion.div>
                        <div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ 📍' + item.remark : ''}"""
    cs_old = cs_old.replace("</motion.div>", "</motion.div>")
    cs_new = """                        <motion.div style="font-weight:600;font-size:14px;">${item.code ? '<span style="color:#1677ff;margin-right:6px;">#' + item.code + '</span>' : ''}${item.name}</motion.div>
                        <motion.div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ <span style="color:#999;font-size:11px;" title="' + String(item.remark||'').replace(/"/g,'&quot;') + '">' + (String(item.remark||'').length>28?String(item.remark||'').slice(0,28)+'…':String(item.remark||'')) + '</span>' : ''}"""
    cs_old2 = """                        <div style="font-weight:600;font-size:14px;">${item.name}</div>
                        <motion.div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ 📍' + item.remark : ''}"""
    cs_old2 = cs_old2.replace("<motion.div", "<motion.div").replace("</motion.div>", "</motion.div>")
    cs_old2 = """                        <div style="font-weight:600;font-size:14px;">${item.name}</div>
                        <div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ 📍' + item.remark : ''}"""
    cs_new = """                        <div style="font-weight:600;font-size:14px;">${item.code ? '<span style="color:#1677ff;margin-right:6px;">#' + item.code + '</span>' : ''}${item.name}</div>
                        <div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ <span style="color:#999;font-size:11px;" title="' + String(item.remark||'').replace(/"/g,'&quot;') + '">' + (String(item.remark||'').length>28?String(item.remark||'').slice(0,28)+'…':String(item.remark||'')) + '</span>' : ''}"""
    if cs_old2 in text:
        text = text.replace(cs_old2, cs_new, 1)
    # index.html already has code in list - ensure remark truncated
    idx_pat = r"\$\{item\.remark \? ' [^']*' \+ item\.remark : ''\}"
    text = re.sub(
        idx_pat,
        "${item.remark ? ' ｜ <span style=\"color:#999;font-size:11px;\" title=\"' + String(item.remark||'').replace(/\"/g,'&quot;') + '\">' + (String(item.remark||'').length>28?String(item.remark||'').slice(0,28)+'…':String(item.remark||'')) + '</span>' : ''}",
        text,
        count=1,
    )
    return text


def patch_submit_url(text: str) -> str:
    return text.replace(
        "            const body = { product_type: ptype, name, length: l, width: w, height: h, remark, stock };\n                url = '/api/dimoldb';",
        "            const code = (document.getElementById('dmfCode') && document.getElementById('dmfCode').value.trim()) || '';\n            const body = { product_type: ptype, name, code, length: l, width: w, height: h, remark, stock };\n            let url = '/api/dimoldb';",
    )


def patch_fill_form_code(text: str) -> str:
    if "dmfCode" not in text or "getElementById('dmfCode')" in text.split("fillDimoldbForm")[1][:800]:
        pass
    insert_after_name = "        document.getElementById('dmfName').value = item.name || '';\n"
    code_line = "        if (document.getElementById('dmfCode')) document.getElementById('dmfCode').value = item.code || '';\n"
    if insert_after_name in text and code_line not in text:
        text = text.replace(insert_after_name, insert_after_name + code_line, 1)
    reset_block = "        document.getElementById('dmfName').value = '';\n"
    code_reset = "        if (document.getElementById('dmfCode')) document.getElementById('dmfCode').value = '';\n"
    if reset_block in text and code_reset not in text:
        text = text.replace(reset_block, reset_block + code_reset, 1)
    return text


def patch_wps(text: str) -> str:
    # 登录恢复不自动打开 WPS（避免首页/刷新自动联网加载）
    text = text.replace(
        "        if (route.sub && document.getElementById('page-' + route.sub)) {",
        "        if (route.sub && route.sub !== 'diemold' && document.getElementById('page-' + route.sub)) {",
        1,
    )
    # 移除 switchSubPage 开头对所有 iframe 的自动赋值（仅 diemold 分支内按需加载）
    block = """        // 如果是子功能页，延迟加载iframe
        const targetIframe = document.querySelector(`#page-${name} iframe[data-src]`);
        if (targetIframe && !targetIframe.src) {
            targetIframe.src = targetIframe.dataset.src;
        }
        
"""
    if block in text:
        text = text.replace(block, "", 1)
    # switchTopPage 仅 erp/jst 懒加载，不含 diemold
    text = text.replace(
        "        if (name === 'diemold' || name === 'erp' || name === 'jst') {",
        "        if (name === 'erp' || name === 'jst') {",
    )
    # diemold：仅用户点击二级导航时加载 iframe
    if "function loadDiemoldIframe()" not in text:
        fn = """
    function loadDiemoldIframe() {
        const iframe = document.querySelector('#page-diemold iframe[data-src]');
        if (!iframe) return;
        if (!iframe.getAttribute('src')) {
            iframe.src = iframe.getAttribute('data-src') || '';
        }
    }
"""
        text = text.replace("    function switchSubPage(name, el) {", fn + "    function switchSubPage(name, el) {", 1)
    text = text.replace(
        "            const iframe = document.querySelector('#page-diemold iframe[data-src]');\n            if (iframe && !iframe.src) iframe.src = iframe.dataset.src;",
        "            loadDiemoldIframe();",
    )
    # iframe 默认空白，保持静止
    text = text.replace(
        '<iframe class="iframe-container" data-src="https://www.kdocs.cn/l/cdIlitRGKpMw"',
        '<iframe class="iframe-container" src="about:blank" data-src="https://www.kdocs.cn/l/cdIlitRGKpMw"',
        1,
    )
    return text


def patch_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    orig = text
    text = insert_helpers(text)
    text = patch_inv_infer(text)
    text = patch_dm_html_remark(text)
    text = patch_home_quick(text)
    text = patch_quote_dim_search(text)
    text = patch_quick_search(text)
    text = patch_dimoldb_list(text)
    text = patch_submit_url(text)
    text = patch_fill_form_code(text)
    if "index_cs" in path.name or "index.html" in path.name:
        text = patch_wps(text)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        print(f"patched {path.name}")
    else:
        print(f"no change {path.name}")


def main() -> None:
    for name in ("index_cs.html", "index.html"):
        p = ROOT / name
        if p.exists():
            patch_file(p)


if __name__ == "__main__":
    main()
