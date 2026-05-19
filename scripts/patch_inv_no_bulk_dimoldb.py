#!/usr/bin/env python3
"""Remove inventory page bulk dimoldb/search fetch from index.html."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for name in ("index.html", "index_production.html"):
    p = ROOT / name
    t = p.read_text(encoding="utf-8")
    start = t.find("let dimoldbMap = {};")
    if start < 0:
        print(name, "skip: no dimoldbMap")
        continue
    end = t.find("items.forEach(item => {", start)
    if end < 0:
        print(name, "skip: no forEach")
        continue
    # keep comment line before if any
    line_start = t.rfind("\n", 0, start) + 1
    prefix = t[line_start:start]
    if "刀模" in prefix or "dimoldb" in prefix.lower():
        line_start = t.rfind("\n", 0, line_start - 1) + 1
    replacement = "            html = '<motion.div style=\"display:flex;flex-direction:column;gap:2px;\">';".replace(
        "<motion.div", "<div"
    ).replace("</motion.div>", "</div>")
    t = t[:line_start] + replacement + "\n" + t[end:]
    # fix dmForRender block
    t = t.replace(
        ": (dimoldbMap[dmKey] || []).slice();",
        ": [];",
    )
    t = t.replace(
        "dmForRender = _invFilterDimoldbInfoForItem(item, dmForRender);\n                const dmHtml",
        "const dmHtml",
    )
    t = t.replace(
        "🔧${m.remark||''}",
        "🔧${(m.code || m.remark || '')}",
    )
    p.write_text(t, encoding="utf-8", newline="\n")
    t = t.replace("\nitems.forEach(item => {", "\n            items.forEach(item => {", 1)
    p.write_text(t, encoding="utf-8", newline="\n")
    print(name, "patched, fffd=", t.count("\ufffd"))
