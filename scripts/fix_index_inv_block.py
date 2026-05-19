#!/usr/bin/env python3
"""Align index.html loadInventory render block with index_production.html."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
idx = ROOT / "index.html"
prod = ROOT / "index_production.html"
t = idx.read_text(encoding="utf-8")
p = prod.read_text(encoding="utf-8")

start_marker = "            if (!items.length) {"
end_marker = "            html += '</motion.div>';"
# production uses </motion.div> no - uses </div>
end_marker = "            html += '</div>';\n            // 分页条"

i0 = t.find(start_marker)
i1 = t.find(end_marker, i0)
if i0 < 0 or i1 < 0:
    raise SystemExit(f"markers not found in index.html i0={i0} i1={i1}")

p0 = p.find(start_marker)
p1 = p.find(end_marker, p0)
if p0 < 0 or p1 < 0:
    raise SystemExit("markers not found in index_production.html")

block = p[p0:p1]
# index.html uses _dmDimCode in other places; production block is fine
t = t[:i0] + block + t[i1:]
idx.write_text(t, encoding="utf-8", newline="\n")
print("ok, fffd=", t.count("\ufffd"))
