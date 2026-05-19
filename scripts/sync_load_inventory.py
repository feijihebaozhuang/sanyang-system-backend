#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
idx = ROOT / "index.html"
prod = ROOT / "index_production.html"
pat = re.compile(
    r"    async function loadInventory\(page, resetPage\) \{.*?\n    \}\n\n    function resetInvForm",
    re.DOTALL,
)
for name, p in (("index", idx), ("prod", prod)):
    t = p.read_text(encoding="utf-8")
    m = pat.search(t)
    if not m:
        raise SystemExit(f"{name}: loadInventory not found")
    if name == "prod":
        prod_block = m.group(0)

t = idx.read_text(encoding="utf-8")
m = pat.search(t)
if not m:
    raise SystemExit("index: loadInventory not found")
t = t[: m.start()] + prod_block + t[m.end() :]
idx.write_text(t, encoding="utf-8", newline="\n")
print("synced loadInventory, fffd=", t.count("\ufffd"))
