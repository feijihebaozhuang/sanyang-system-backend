# 刀模库重复数据 — 给 C 的处理说明

## 数据概况（已核对方向）

| 类别 | 数量 | 处理 |
|------|------|------|
| 纯重复（同 code + 同规格，仅 id 不同） | **3 条** | 可自动删，保留最小 `id` |
| 冲突 code（同 code 多规格） | **3 个**：1450、6036、8361 | 导出 CSV 人工拆分/改 code |
| 无 code「孤魂」 | **9,467 条** | 需与业务方定方案后再动 |
| 可用唯一 code | **18,111** | 冲突修完后可用 |

## 1. 删 3 条纯重复（服务器执行）

```bash
cd /www/feijihe/stable   # 或 repo，需有 .env
python3 scripts/dimoldb_data_cleanup.py audit
python3 scripts/dimoldb_data_cleanup.py delete-exact-dupes          # 先预览 ids
python3 scripts/dimoldb_data_cleanup.py delete-exact-dupes --apply  # 确认后执行
```

等价 SQL 思路（保留每组最小 id）：

```sql
-- 务必先 SELECT 确认仅 3 条再 DELETE
SELECT d1.id AS drop_id, d2.id AS keep_id, d1.code, d1.length, d1.width, d1.height
FROM dimoldb d1
JOIN dimoldb d2
  ON TRIM(d1.code) = TRIM(d2.code) AND TRIM(d1.code) <> ''
 AND d1.product_type = d2.product_type
 AND ROUND(d1.length,3) = ROUND(d2.length,3)
 AND ROUND(d1.width,3) = ROUND(d2.width,3)
 AND ROUND(d1.height,3) = ROUND(d2.height,3)
 AND TRIM(IFNULL(d1.name,'')) = TRIM(IFNULL(d2.name,''))
 AND TRIM(IFNULL(d1.remark,'')) = TRIM(IFNULL(d2.remark,''))
 AND d1.id > d2.id;
```

## 2. 冲突 code 1450 / 6036 / 8361

```bash
python3 scripts/dimoldb_data_cleanup.py export-conflicts
```

生成文件在 `scripts/output/dimoldb_cleanup/`：

- `conflict_codes_*.csv` — 上述 3 个 code 共 12 行明细
- `all_multi_spec_codes_*.csv` — 库内所有「一 code 多规格」列表

**人工原则**：一个 code 只应对应一种长宽高（及内外径若适用）；错映射行应改 `code` 或删重复导入行，勿只改 remark。

## 3. 无 code 的 9,467 条 — 建议方案（待与 C 确认）

| 方案 | 说明 | 风险 |
|------|------|------|
| **A. 批量补 code** | remark 已是 A805/B257 等编号 → 写入 `code` 字段 | 需确认与快麦/订单编码体系一致 |
| **B. 按规格生成新 code** | 无历史编号时按规则生成（如 `Koudi-{L}x{W}x{H}`） | 可能与现有 18k code 撞号，要前缀+查重 |
| **C. 归档/软删** | 标记不可用，匹配逻辑排除 | 若仍被订单引用会「未匹配刀模」 |
| **D. 分类型处理** | 扣底盒/双插盒用 remark→code；其余先导出再定 | 推荐先做 |

```bash
python3 scripts/dimoldb_data_cleanup.py export-no-code --limit 10000
```

先看 `no_code_by_type_*.csv` 和 `no_code_sample_*.csv` 再定 A/B/C。

**不建议**在未确认前整表 DELETE 无 code 记录。

## 4. 导入侧防再犯

- 导入应带 **编码列**，写入 `code`；remark 仅作位置/备注
- 导入前按 `(code, length, width, height, product_type)` 查重，已存在则 skip 或 update
- 避免重复跑全量导入脚本（历史「抽风」原因）
