# 刀模 Excel 放这里

标准 8 文件（已验证 2026-05-21）：

| 文件 | 格式 | 有效行 |
|------|------|--------|
| 全量刀模_第1～4批(7列).xlsx | 7 列 | 5000+5000+5000+3114 |
| 全量刀模v2_第1～4批9列.xlsx | 9 列 | 同上 |

合并去重后 **18111 条**，**编码 100% 有值**。7 列与 v2 九列同批数据一致（第 1 批 key 重合 4999/4999）。

把 **7 列** 和/或 **9 列** 刀模表（`.xlsx`）复制到本目录，然后在项目根目录执行：

```bash
# 1. 先看表头与行数（不写库）
python scripts/import_dimoldb_auto.py --audit

# 2. 多文件合并后覆盖进 MySQL（推荐）
python scripts/import_dimoldb_auto.py --merge --overwrite

# 3. 只导入单个文件
python scripts/import_dimoldb_auto.py 你的刀模.xlsx --overwrite

# 4. 八文件合并为 JSON（本地已生成 merge_summary.json）
python scripts/merge_dimoldb_inbox.py

# 5. 213 上写入 MySQL（二选一）
python scripts/import_dimoldb_auto.py data/import/dimoldb --merge --overwrite
# 或
python scripts/import_dimoldb_merged_json.py data/import/dimoldb/dimoldb_merged.json
```

7 列标准表头：产品类型、名称、编码、备注、长(cm)、宽(cm)、高(cm)

9 列会多：生产规格、快麦商品映射（会入库但匹配仍只用长宽厚）
