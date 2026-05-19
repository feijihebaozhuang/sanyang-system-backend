#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "index.html"
raw = p.read_text(encoding="utf-8")
crlf = "\r\n" in raw
t = raw.replace("\r\n", "\n")

# --- form (after dmfName block) ---
needle = 'placeholder="\u4f8b\u5982\uff1a\u98de\u673a\u76d220\u00d715\u00d710"'
if needle not in t:
    raise SystemExit("dmfName placeholder not found")
t = t.replace(
    needle,
    'placeholder="\u7f16\u53f7\u6216\u63cf\u8ff0\uff0c\u5982 51398"',
    1,
)
insert_after = (
    'placeholder="\u7f16\u53f7\u6216\u63cf\u8ff0\uff0c\u5982 51398" onfocus="this.select()">\n'
    "                    </motion>\n"
    '                    <div style="margin-bottom:8px;">\n'
    '                        <label style="font-size:12px;color:#666;display:block;margin-bottom:4px;">'
    "\u4ea7\u54c1\u7c7b\u578b</label>"
)
insert_after = insert_after.replace("</motion>", "</" + "div>").replace(
    '<motion style="margin-bottom:8px;">', '<' + "motion" + ' style="margin-bottom:8px;">'
)
# fix insert_after properly
dv = "div"
insert_after = (
    'placeholder="\u7f16\u53f7\u6216\u63cf\u8ff0\uff0c\u5982 51398" onfocus="this.select()">\n'
    f"                    </{dv}>\n"
    f'                    <{dv} style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px;">\n'
    f"                        <{dv}>\n"
    '                            <label style="font-size:12px;color:#666;display:block;margin-bottom:4px;">'
    "\u7f16\u7801</label>\n"
    '                            <input type="text" id="dmfCode" style="width:100%;padding:8px 10px;'
    'border:1px solid #d9d9d9;border-radius:6px;font-size:13px;" onfocus="this.select()">\n'
    f"                        </{dv}>\n"
    f"                        <{dv}>\n"
    '                            <label style="font-size:12px;color:#666;display:block;margin-bottom:4px;">'
    "\u5feb\u9ea6\u5546\u54c1\u6620\u5c04</label>\n"
    '                            <input type="text" id="dmfKmMapping" style="width:100%;padding:8px 10px;'
    'border:1px solid #d9d9d9;border-radius:6px;font-size:13px;" onfocus="this.select()">\n'
    f"                        </{dv}>\n"
    f"                    </{dv}>\n"
    f'                    <{dv} style="margin-bottom:8px;">\n'
    '                        <label style="font-size:12px;color:#666;display:block;margin-bottom:4px;">'
    "\u751f\u4ea7\u89c4\u683c</label>\n"
    '                        <input type="text" id="dmfProductionSpec" style="width:100%;padding:8px 10px;'
    'border:1px solid #d9d9d9;border-radius:6px;font-size:13px;" '
    'placeholder="\u5982 52.5\u00d739.5\u00d78.5" onfocus="this.select()">\n'
    f"                    </{dv}>\n"
    f'                    <{dv} style="margin-bottom:8px;">\n'
    '                        <label style="font-size:12px;color:#666;display:block;margin-bottom:4px;">'
    "\u4ea7\u54c1\u7c7b\u578b</label>"
)
anchor = (
    'placeholder="\u7f16\u53f7\u6216\u63cf\u8ff0\uff0c\u5982 51398" onfocus="this.select()">\n'
    f"                    </{dv}>\n"
    f'                    <{dv} style="margin-bottom:8px;">\n'
    '                        <label style="font-size:12px;color:#666;display:block;margin-bottom:4px;">'
    "\u4ea7\u54c1\u7c7b\u578b</label>"
)
if "dmfCode" not in t:
    if anchor not in t:
        raise SystemExit("form anchor not found")
    t = t.replace(anchor, insert_after, 1)

# --- helpers ---
marker = "    async function loadDimoldbList(page, resetPage) {"
helpers = """    function _dmEsc(s) {
        if (s == null || s === '') return '';
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
    }
    function _dmShort(s, n) {
        if (!s) return '';
        s = String(s);
        return s.length > n ? s.slice(0, n) + '\\u2026' : s;
    }

"""
if "_dmEsc" not in t:
    t = t.replace(marker, helpers + marker, 1)

# --- list row ---
t = t.replace(
    '<motion style="font-weight:600;font-size:14px;">${item.name}</motion>'.replace(
        "motion", "div"
    ),
    '<motion style="font-weight:600;font-size:14px;">${item.code ? \'<span style="color:#1677ff;margin-right:6px;">#\' + _dmEsc(item.code) + \'</span>\' : \'\'}${_dmEsc(item.name)}</motion>'.replace(
        "motion", "motion"
    ),
)
# fix list replacements with dv variable
name_old = f'<{dv} style="font-weight:600;font-size:14px;">${{item.name}}</{dv}>'
name_new = (
    f'<{dv} style="font-weight:600;font-size:14px;">'
    "${item.code ? '<span style=\"color:#1677ff;margin-right:6px;\">#' + _dmEsc(item.code) + '</span>' : ''}"
    "${_dmEsc(item.name)}"
    f"</{dv}>"
)
if name_old in t:
    t = t.replace(name_old, name_new, 1)

rmk_old = "${item.remark ? ' \uff5c \ud83d\udccd' + item.remark : ''}"
rmk_new = (
    "${item.production_spec ? ' \uff5c \u89c4\u683c:' + _dmEsc(_dmShort(item.production_spec, 18)) : ''}\n"
    '                            ${item.remark ? \' \uff5c <span title="\' + _dmEsc(item.remark) + \'">\' + _dmEsc(_dmShort(item.remark, 20)) + \'</span>\' : \'\'}'
)
if rmk_old in t:
    t = t.replace(rmk_old, rmk_new, 1)

meta_line = f'                        <{dv} style="font-size:12px;color:#666;margin-top:2px;">'
if meta_line in t and "line-height:1.4" not in t:
    t = t.replace(
        meta_line,
        f'                        <{dv} style="font-size:12px;color:#666;margin-top:2px;line-height:1.4;">',
        1,
    )

# --- form JS ---
if "dmfCode" in t and "getElementById('dmfCode')" not in t:
    pass
t = t.replace(
    "        document.getElementById('dmfRemark').value = '';\n"
    "        document.getElementById('dmfStock').value = '0';",
    "        document.getElementById('dmfCode').value = '';\n"
    "        document.getElementById('dmfProductionSpec').value = '';\n"
    "        document.getElementById('dmfKmMapping').value = '';\n"
    "        document.getElementById('dmfRemark').value = '';\n"
    "        document.getElementById('dmfStock').value = '0';",
    1,
)
t = t.replace(
    "        document.getElementById('dmfRemark').value = item.remark || '';\n"
    "        document.getElementById('dmfStock').value = item.stock ?? '0';",
    "        document.getElementById('dmfCode').value = item.code || '';\n"
    "        document.getElementById('dmfProductionSpec').value = item.production_spec || '';\n"
    "        document.getElementById('dmfKmMapping').value = item.km_mapping_code || '';\n"
    "        document.getElementById('dmfRemark').value = item.remark || '';\n"
    "        document.getElementById('dmfStock').value = item.stock ?? '0';",
    1,
)
t = t.replace(
    "        const remark = document.getElementById('dmfRemark').value.trim();\n"
    "        const type_class = document.getElementById('dmfTypeClass').value;",
    "        const code = document.getElementById('dmfCode').value.trim();\n"
    "        const production_spec = document.getElementById('dmfProductionSpec').value.trim();\n"
    "        const km_mapping_code = document.getElementById('dmfKmMapping').value.trim();\n"
    "        const remark = document.getElementById('dmfRemark').value.trim();\n"
    "        const type_class = document.getElementById('dmfTypeClass').value;",
    1,
)
t = t.replace(
    "            const body = { product_type: ptype, name, length: l, width: w, height: h, remark, stock, type_class, opens };",
    "            const body = { product_type: ptype, name, code, production_spec, km_mapping_code, length: l, width: w, height: h, remark, stock, type_class, opens };",
    1,
)

t = t.replace(
    "/static/auth_session.js?v=20260518b",
    "/static/auth_session.js?v=20260520",
    1,
)

out = t.replace("\n", "\r\n") if crlf else t
p.write_text(out, encoding="utf-8")
print("OK", "dmfCode" in out, "_dmEsc" in out)
