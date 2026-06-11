#!/usr/bin/env python3
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "index.html"
t = p.read_text(encoding="utf-8")
t = t.replace("</motion>", "</div>")
rmk_old = "${item.remark ? ' \uff5c \ud83d\udccd' + item.remark : ''}"
rmk_new = (
    "${item.production_spec ? ' \uff5c \u89c4\u683c:' + _dmEsc(_dmShort(item.production_spec, 18)) : ''}\n"
    '                            ${item.remark ? \' \uff5c <span title="\' + _dmEsc(item.remark) + \'">\' + _dmEsc(_dmShort(item.remark, 20)) + \'</span>\' : \'\'}'
)
t = t.replace(rmk_old, rmk_new)
p.write_text(t, encoding="utf-8")
print("OK")
