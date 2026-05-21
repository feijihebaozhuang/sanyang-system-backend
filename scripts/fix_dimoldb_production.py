#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复生产端刀模库前端：let html、保存 url、编码字段、列表显示 code。"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROD = ROOT / "index_production.html"

HELPERS = """
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

CODE_FIELDS = """
                    <div style="margin-bottom:8px;">
                        <label style="font-size:12px;color:#666;display:block;margin-bottom:4px;">刀模编码</label>
                        <input type="text" id="dmfCode" style="width:100%;padding:8px 10px;border:1px solid #d9d9d9;border-radius:6px;font-size:14px;" placeholder="必填建议：与快麦/订单一致" onfocus="this.select()">
                    </div>
                    <div style="margin-bottom:8px;">
                        <label style="font-size:12px;color:#666;display:block;margin-bottom:4px;">生产规格</label>
                        <input type="text" id="dmfProductionSpec" style="width:100%;padding:8px 10px;border:1px solid #d9d9d9;border-radius:6px;font-size:14px;" placeholder="可选" onfocus="this.select()">
                    </div>
"""


def main() -> None:
    t = PROD.read_text(encoding="utf-8")
    marker = "    // ===== 固定刀模库 ====="
    if "_dmDimCode" not in t and marker in t:
        t = t.replace(marker, HELPERS + marker, 1)

    if 'id="dmfCode"' not in t:
        t = t.replace(
            '<label style="font-size:12px;color:#666;display:block;margin-bottom:4px;">刀模名称</label>',
            '<label style="font-size:12px;color:#666;display:block;margin-bottom:4px;">刀模名称</label>',
            1,
        )
        anchor = '<input type="text" id="dmfName" style="width:100%;'
        if anchor in t:
            t = t.replace(
                anchor,
                CODE_FIELDS.strip() + "\n                    " + anchor,
                1,
            )

    t = re.sub(
        r"(if \(!items\.length\) \{[^}]+\}\s*)\s*html = '<div style=\"display:flex;flex-direction:column;gap:2px;\">';",
        r"\1\n            let html = '<div style=\"display:flex;flex-direction:column;gap:2px;\">';",
        t,
        count=1,
    )

    old_list = """                        <div style="font-weight:600;font-size:14px;">${item.name}</div>
                        <div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ 📍' + item.remark : ''}"""
    new_list = """                        <div style="font-weight:600;font-size:14px;">${item.code ? '<span style="color:#1677ff;margin-right:6px;">#' + item.code + '</span>' : '<span style="color:#fa8c16;margin-right:6px;">未编码</span>'}${item.name}</div>
                        <div style="font-size:12px;color:#666;margin-top:2px;">
                            ${tlabel} ｜ ${item.length}×${item.width}×${item.height} cm
                            ${item.remark ? ' ｜ <span style="color:#999;font-size:11px;" title="' + String(item.remark||'').replace(/"/g,'&quot;') + '">' + (String(item.remark||'').length>28?String(item.remark||'').slice(0,28)+'…':String(item.remark||'')) + '</span>' : ''}"""
    if old_list in t:
        t = t.replace(old_list, new_list, 1)

    t = t.replace(
        "document.getElementById('dmfType').value = item.product_type || 'airbox';",
        "document.getElementById('dmfType').value = item.product_type || 'zhengsquare';",
    )
    if "dmfCode" in t and "getElementById('dmfCode').value = item.code" not in t:
        t = t.replace(
            "document.getElementById('dmfName').value = item.name || '';\n",
            "document.getElementById('dmfName').value = item.name || '';\n"
            "        if (document.getElementById('dmfCode')) document.getElementById('dmfCode').value = item.code || '';\n"
            "        if (document.getElementById('dmfProductionSpec')) document.getElementById('dmfProductionSpec').value = item.production_spec || '';\n",
            1,
        )
        t = t.replace(
            "document.getElementById('dmfName').value = '';\n",
            "document.getElementById('dmfName').value = '';\n"
            "        if (document.getElementById('dmfCode')) document.getElementById('dmfCode').value = '';\n"
            "        if (document.getElementById('dmfProductionSpec')) document.getElementById('dmfProductionSpec').value = '';\n",
            1,
        )

    broken_submit = """            const body = { product_type: ptype, name, length: l, width: w, height: h, remark, stock, type_class, opens };
                url = '/api/dimoldb';
            let method = 'POST';"""
    fixed_submit = """            const code = (document.getElementById('dmfCode') && document.getElementById('dmfCode').value.trim()) || '';
            const production_spec = (document.getElementById('dmfProductionSpec') && document.getElementById('dmfProductionSpec').value.trim()) || '';
            const body = { product_type: ptype, name, code, production_spec, length: l, width: w, height: h, remark, stock, type_class, opens };
            let url = '/api/dimoldb';
            let method = 'POST';"""
    if broken_submit in t:
        t = t.replace(broken_submit, fixed_submit, 1)
    elif "let url = '/api/dimoldb'" not in t and "async function submitDimoldbForm" in t:
        t = t.replace(
            "const body = { product_type: ptype, name, length: l, width: w, height: h, remark, stock, type_class, opens };",
            fixed_submit.split("let url")[0].strip().split("const code")[1].strip()
            if False else fixed_submit.split("\n            let url")[0].replace("            ", "            const ", 1),
            1,
        )

    PROD.write_text(t, encoding="utf-8", newline="\n")
    print("patched index_production.html")

    rebuild = ROOT / "scripts" / "rebuild_index_html.py"
    if rebuild.exists():
        subprocess.run([sys.executable, str(rebuild)], check=True, cwd=str(ROOT))
        patch = ROOT / "scripts" / "patch_dimoldb_frontend.py"
        # extend patch to production in subprocess inline
        idx = ROOT / "index.html"
        pt = idx.read_text(encoding="utf-8")
        # ensure let html in loadDimoldbList on index.html
        pt = re.sub(
            r"(if \(!items\.length\) \{[^}]+\}\s*)\s*html = '<div style=\"display:flex;flex-direction:column;gap:2px;\">';",
            r"\1\n            let html = '<div style=\"display:flex;flex-direction:column;gap:2px;\">';",
            pt,
            count=1,
        )
        broken2 = """            const body = { product_type: ptype, name, length: l, width: w, height: h, remark, stock, type_class, opens };
                url = '/api/dimoldb';
            let method = 'POST';"""
        if broken2 in pt:
            pt = pt.replace(broken2, fixed_submit, 1)
        idx.write_text(pt, encoding="utf-8", newline="\n")
        print("patched index.html submit + let html")


if __name__ == "__main__":
    main()
