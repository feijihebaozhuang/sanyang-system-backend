#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT / "scripts" / "rebuild_index_html.py")], check=True)
idx = ROOT / "index.html"
t = idx.read_text(encoding="utf-8")
marker = "    /** 与 dimoldb_store.infer_inner_outer 一致 */"
parts = t.split(marker)
if len(parts) > 2:
    rest = parts[2]
    after = rest.split("    // ===== 固定刀模库 =====", 1)
    t = parts[0] + marker + parts[1] + "    // ===== 固定刀模库 =====" + after[-1]
t = t.replace(
    "let html = '<div style=\\\"display:flex;flex-direction:column;gap:2px;\\\">';",
    "let html = '<div style=\"display:flex;flex-direction:column;gap:2px;\">';",
)
idx.write_text(t, encoding="utf-8", newline="\n")
print("ok fffd", t.count("\ufffd"), "helpers", t.count("function _dmDimCode"))
