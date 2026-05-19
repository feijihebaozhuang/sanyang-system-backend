#!/usr/bin/env python3
"""Apply dimoldb UI fixes to index_cs.html and index.html"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MARK = "    // ===== 固定刀模库 ====="
HELPERS = """
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

""" + MARK


def fix_cs(text: str) -> str:
    if "_dmInferInnerOuter" not in text:
        text = text.replace(MARK, HELPERS)

    text = text.replace(
        """                        <div style="font-weight:600;font-size:14px;">${item.name}</div>
                        <div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ 📍' + item.remark : ''}""",
        """                        <div style="font-weight:600;font-size:14px;">${item.code ? '<span style="color:#1677ff;margin-right:6px;">#' + item.code + '</span>' : ''}${item.name}</div>
                        <motion.div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ <span style="color:#999;font-size:11px;" title="' + String(item.remark||'').replace(/"/g,'&quot;') + '">' + (String(item.remark||'').length>28?String(item.remark||'').slice(0,28)+'…':String(item.remark||'')) + '</span>' : ''}""".replace(
            "<motion.div", "<div"
        ).replace("</motion.div>", "</motion.div>"),
        1,
    )

    text = text.replace(
        "            const body = { product_type: ptype, name, length: l, width: w, height: h, remark, stock };\n                url = '/api/dimoldb';",
        "            const code = (document.getElementById('dmfCode') && document.getElementById('dmfCode').value.trim()) || '';\n            const body = { product_type: ptype, name, code, length: l, width: w, height: h, remark, stock };\n            let url = '/api/dimoldb';",
    )
    if "dmfCode').value = item.code" not in text:
        text = text.replace(
            "        document.getElementById('dmfName').value = item.name || '';\n        document.getElementById('dmfType').value",
            "        document.getElementById('dmfName').value = item.name || '';\n        if (document.getElementById('dmfCode')) document.getElementById('dmfCode').value = item.code || '';\n        document.getElementById('dmfType').value",
        )
    if "dmfCode').value = ''" not in text.split("resetDimoldbForm")[1][:800]:
        text = text.replace(
            "        document.getElementById('dmfName').value = '';\n        document.getElementById('dmfL').value = '';",
            "        document.getElementById('dmfName').value = '';\n        if (document.getElementById('dmfCode')) document.getElementById('dmfCode').value = '';\n        document.getElementById('dmfL').value = '';",
        )

    text = text.replace(
        """                    let dmDimType = '';
                    if (m.name.includes('(内)') || m.name.includes('内径')) dmDimType = 'inner';
                    else if (m.name.includes('(外)') || m.name.includes('外径')) dmDimType = 'outer';
                    let relatedInv = invByDim[specKey] || [];
                    if (dmDimType) {
                        relatedInv = relatedInv.filter(ri => ri.dim_type === dmDimType);
                    }""",
        """                    const dmDimType = _dmInferInnerOuter(m);
                    let relatedInv = invByDim[specKey] || [];
                    relatedInv = relatedInv.filter(ri => _dmInvDimMatch(dmDimType, ri.dim_type));""",
    )
    text = text.replace(
        "+ '<span style=\"color:#1677ff;\">📍 ' + (m.remark || '未标注位置') + '</span>'",
        "+ '<span style=\"color:#1677ff;\">编码 ' + _dmDimCode(m) + '</span>'",
    )
    text = text.replace(
        """                        let mDim = '';
                        if (m.name.includes('(内)') || m.name.includes('内径')) mDim = 'inner';
                        else if (m.name.includes('(外)') || m.name.includes('外径')) mDim = 'outer';""",
        "                        const mDim = _dmInferInnerOuter(m);",
    )
    text = text.replace(
        """                    const isInner = m.remark && m.remark.includes('内');
                    const isOuter = m.remark && m.remark.includes('外');""",
        """                    const mDimQ = _dmInferInnerOuter(m);
                    const isInner = mDimQ === 'inner';
                    const isOuter = mDimQ === 'outer';""",
    )
    text = text.replace(
        "${m.remark ? `<div style=\"font-size:13px;color:#e67e22;margin-top:4px;font-weight: bold;\">📍 ${m.remark}</div>` : ''}",
        "${`<div style=\"font-size:12px;color:#888;margin-top:4px;\">编码 ${_dmDimCode(m)}</div>`}",
    )
    text = text.replace("🔧${m.remark||''}", "🔧${_dmDimCode(m)}")

    text = text.replace(
        "        if (route.sub && document.getElementById('page-' + route.sub)) {",
        "        if (route.sub && route.sub !== 'diemold' && document.getElementById('page-' + route.sub)) {",
        1,
    )
    block = """        // 如果是子功能页，延迟加载iframe
        const targetIframe = document.querySelector(`#page-${name} iframe[data-src]`);
        if (targetIframe && !targetIframe.src) {
            targetIframe.src = targetIframe.dataset.src;
        }
        
"""
    if block in text:
        text = text.replace(block, "")
    text = text.replace(
        "        if (name === 'diemold' || name === 'erp' || name === 'jst') {",
        "        if (name === 'erp' || name === 'jst') {",
    )
    if "function loadDiemoldIframe()" not in text:
        text = text.replace(
            "    function switchSubPage(name, el) {",
            """    function loadDiemoldIframe() {
        const iframe = document.querySelector('#page-diemold iframe[data-src]');
        if (!iframe) return;
        const cur = iframe.getAttribute('src') || '';
        if (!cur || cur === 'about:blank') {
            iframe.src = iframe.getAttribute('data-src') || '';
        }
    }

    function switchSubPage(name, el) {""",
        )
    text = text.replace(
        "            if (iframe && !iframe.src) iframe.src = iframe.dataset.src;",
        "            loadDiemoldIframe();",
    )
    if 'src="about:blank" data-src="https://www.kdocs.cn' not in text:
        text = text.replace(
            '<iframe class="iframe-container" data-src="https://www.kdocs.cn/l/cdIlitRGKpMw"',
            '<iframe class="iframe-container" src="about:blank" data-src="https://www.kdocs.cn/l/cdIlitRGKpMw"',
            1,
        )
    return text


def fix_index(text: str) -> str:
    if "_dmInferInnerOuter" not in text:
        text = text.replace(MARK, HELPERS)
    text = re.sub(
        r"function _invInferDimoldbRowType\(m\) \{[\s\S]*?return '';\s*\}",
        "function _invInferDimoldbRowType(m) { return _dmInferInnerOuter(m); }",
        text,
        count=1,
    )
    if "const invBySpec" in text:
        text = text.replace(
            """            const invBySpec = {};
            for (const inv of invItems) {
                const spec = inv.spec || inv.name || '';
                if (!invBySpec[spec]) invBySpec[spec] = [];
                invBySpec[spec].push(inv);
            }""",
            """            const invByDim = {};
            for (const inv of invItems) {
                const dk = inv.length + 'x' + inv.width + 'x' + inv.height;
                if (!invByDim[dk]) invByDim[dk] = [];
                invByDim[dk].push(inv);
            }""",
        )
        text = re.sub(
            r"let dmDimType = '';[\s\S]*?if \(dmDimType\) \{[\s\S]*?relatedInv = relatedInv\.filter\(ri => ri\.dim_type === dmDimType\);\s*\}",
            """const dmDimType = _dmInferInnerOuter(m);
                    let relatedInv = invByDim[specKey] || [];
                    relatedInv = relatedInv.filter(ri => _dmInvDimMatch(dmDimType, ri.dim_type));""",
            text,
            count=1,
        )
    text = re.sub(
        r"\+ '<span style=\"color:#1677ff;\">[^']*' \+ \(m\.remark \|\| [^)]+\) \+ '</span>'",
        "+ '<span style=\"color:#1677ff;\">编码 ' + _dmDimCode(m) + '</span>'",
        text,
        count=1,
    )
    text = text.replace(
        """                        let mDim = '';
                        if (m.name.includes('(内)') || m.name.includes('内径')) mDim = 'inner';
                        else if (m.name.includes('(外)') || m.name.includes('外径')) mDim = 'outer';""",
        "                        const mDim = _dmInferInnerOuter(m);",
    )
    text = text.replace("🔧${m.remark||''}", "🔧${_dmDimCode(m)}")
    return text


def strip_motion(s: str) -> str:
    return s.replace("<motion.div", "<div").replace("</motion.div>", "</div>")


def main():
    for name, fn in (("index_cs.html", fix_cs), ("index.html", fix_index)):
        p = ROOT / name
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        t2 = strip_motion(fn(t))
        if t2 != t:
            p.write_text(t2, encoding="utf-8")
            print("patched", name)
        else:
            print("unchanged", name)


if __name__ == "__main__":
    main()
