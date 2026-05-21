# 刀模 Excel 放这里

把 **7 列** 和/或 **9 列** 刀模表（`.xlsx`）复制到本目录，然后在项目根目录执行：

```bash
# 1. 先看表头与行数（不写库）
python scripts/import_dimoldb_auto.py --audit

# 2. 多文件合并后覆盖进 MySQL（推荐）
python scripts/import_dimoldb_auto.py --merge --overwrite

# 3. 只导入单个文件
python scripts/import_dimoldb_auto.py 你的刀模.xlsx --overwrite
```

7 列标准表头：产品类型、名称、编码、备注、长(cm)、宽(cm)、高(cm)

9 列会多：生产规格、快麦商品映射（会入库但匹配仍只用长宽厚）
