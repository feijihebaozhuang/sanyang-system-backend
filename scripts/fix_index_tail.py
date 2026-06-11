# -*- coding: utf-8 -*-
"""修复 rebuild 误把 batchCalc 插入 prod_ui 外链标签内的问题。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "index.html"
t = p.read_text(encoding="utf-8")
marker = '<script src="/static/prod_ui.js?v=20260520c">'
idx = t.rfind(marker)
if idx < 0:
    raise SystemExit("prod_ui marker not found")
tail = """<script>
async function batchCalcMaterialOrders() {
    const ids = getSelectedProdIds();
    if (!ids.length) { alert('请先勾选要打单的订单'); return; }
    if (typeof window.batchCalcMaterialOrdersImpl === 'function') {
        return window.batchCalcMaterialOrdersImpl(ids);
    }
    alert('算料模块未加载，请刷新页面');
}
</script>
<script src="/static/prod_ui.js?v=20260520c"></script>

</body>
</html>
"""
p.write_text(t[:idx] + tail, encoding="utf-8", newline="\n")
print("fixed", p.name)
