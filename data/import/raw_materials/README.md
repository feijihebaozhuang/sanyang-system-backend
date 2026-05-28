# 原材料库存快照（纸箱快麦执行标准）

## 文件

**`raw_materials.json`** — 从 MySQL `raw_materials` 导出的只读快照，供本地算料 / 桌面脚本使用。

| 字段 | 说明 |
|------|------|
| `supplier` | 供应商 |
| `name` | 材料名（如 D6D（E坑）、新浦 B坑） |
| `paper_width` | 纸宽 |
| `paper_length` | 纸长 |
| `qty` | 库存数量 |

当前：**1761 条**（小马哥 2026-05 导出并 push）。

---

## 谁维护、怎么更新

| 场景 | 做法 |
|------|------|
| **小马哥在 87 / 后台改库存** | 87 执行 `python3 scripts/export_raw_materials_json.py` → commit + push |
| **C 在后台维护完** | 通知小马哥或 Cursor：**拉新版本 JSON**，或说「原材料库存变了，重新导出 push」 |
| **本地重跑纸箱更新表** | `git pull` 后跑 `快麦对接/scripts/_build_kuaimai_carton_material.py` |

**铁律**：Python 算料只读此 JSON / MySQL，**禁止**用硬编码覆盖 JSON 里已有内容（见 `.cursor/rules/config-json-iron-rule.mdc`）。

---

## 读取优先级（桌面脚本 `_build_kuaimai_carton_material.py`）

1. 本机 MySQL `raw_materials`（87 上直连 RDS 时）
2. **`sanyang-system/data/import/raw_materials/raw_materials.json`**（本地开发 / 无库时）
3. 桌面兜底 `原材料库存.json`（旧路径，可删）

算料核心：`material_calc.py` → `match_paper()` / `format_carton_kuaimai_exec_std()`。

---

## 小马哥导出命令（87 stable）

```bash
cd /www/feijihe/stable
source venv/bin/activate
python3 scripts/export_raw_materials_json.py
cd /www/feijihe/repo
git add data/import/raw_materials/raw_materials.json
git commit -m "原材料库存快照更新"
git push origin main
```

---

## 本地 C 侧

库存变动后若要重生成纸箱执行标准 Excel：

```bash
cd D:\Desktop\sanyang-system
git pull origin main
python D:\Desktop\快麦对接\scripts\_build_kuaimai_carton_material.py
```

输出：`快麦对接/已上传/纸箱_快麦更新_用料_合并.xlsx`
