# 刀模库恢复方案（7 列表头 · 先稳再改）

## 结论（直接回答）

- **是**：当前阶段应 **固定 Excel 7 列**，表头 **暂时不要** 加「生产规格」「快麦商品映射」。
- **不必** 为刀模 alone 把整站 Git 硬回滚到 5.20 凌晨（会丢掉订单 MySQL 缓存、打单修复等）。
- **推荐顺序**：
  1. 部署本仓库 **7 列回退** 的后端 + 前端（`main` 最新）
  2. 用 **最新刀模 Excel（7 列）** 在服务器 **覆盖导入** MySQL
  3. 业务验证刀模库 / 库存 / 打单匹配正常
  4. **以后** 再单独立项加列、改匹配（一步一步，每步可回滚）

## 标准 7 列（与改表头前一致）

| 列序 | 表头 |
|------|------|
| 1 | 产品类型 |
| 2 | 名称 |
| 3 | 编码 |
| 4 | 备注 |
| 5 | 长(cm) |
| 6 | 宽(cm) |
| 7 | 高(cm) |

导出 Excel 在此基础上可加：**序号**、**创建时间**（不算在导入必填 7 列里）。

## 为何「改表头后全乱」

1. **01:41** 起导入模板变成 9 列，旧 Excel 列错位 → 编码/备注/尺寸写错列。
2. 代码从 **remark / production_spec 解析尺寸** → 一条刀模匹配到多条库存。
3. 生产端页面多次合并/重建，保存刀模 `url` 曾写错。
4. MySQL 里历史脏数据（无 code、重复导入）仍在，表头一变更显乱。

本次代码已：**恢复 7 列模板与导入映射**；匹配 **只用 length/width/height 字段**，不再从备注扒尺寸。

## 213 服务器操作步骤

### 1. 拉代码并部署

```bash
cd /www/feijihe/repo && git pull origin main
./deploy.sh
cp /www/feijihe/repo/index.html /www/feijihe/stable/index.html
chown admin:sanyang /www/feijihe/stable/index.html
# 从 /www/feijihe/stable 重启 3001 / 3002
```

### 2. 备份当前刀模表（必做）

```bash
mysqldump -u... -p... sanyang dimoldb > /home/admin/backup/feijihe/dimoldb_before_restore_$(date +%Y%m%d_%H%M).sql
```

### 3. 用最新 7 列 Excel 全量覆盖

- 页面：刀模库 → 导入 Excel，模式选 **覆盖（overwrite）**
- 或命令行：

```bash
cd /www/feijihe/stable
python3 scripts/import_dimoldb_7col.py /path/to/最新刀模.xlsx --overwrite
```

导入前请确认表头行含 **「名称」**，且为上述 7 列（多出来的列会被忽略）。

### 4. 验证

- 刀模库列表：名称 + 尺寸 + 编码/备注显示正常
- 库存页：匹配到的刀模数量合理（不再一片「乱匹配」）
- 打单：刀模编码与以前业务印象一致
- 新增/编辑一条刀模 → 保存成功

### 5. 清缓存

导入后重启 3002，或等 `DIMOLDB_CACHE_TTL_SEC`（默认 120s）过期。

## 若必须「整站回到 5.20 凌晨 2 点前」

仅当订单/配置也要一并回退时：

```bash
cd /www/feijihe/repo
git checkout ec6a356   # 01:11，刀模仍为 dimoldb.json，7 列
# 或 535d9fa          # 01:56，已 MySQL+9列（不推荐为刀模锚点）
```

同时恢复：

- `stable/dimoldb.json` 或 MySQL 备份
- `data.json`、`.env`（若有当时备份）

**一般不建议**：会丢失 5.20 白天订单缓存、打单、快麦同步等修复。

## 以后如何「一步一步改刀模代码」

1. 只改 **分支** / 小提交，不动 `main` 直推表头。
2. 每步：7 列 Excel 小样 → 导入测试环境 → 看库存/打单 diff。
3. 加列时：先 **DB 加列可空** → 再 **导出多列** → 最后 **导入识别多列**（顺序不能反）。
4. 文档更新 `LEGACY_IMPORT_HEADERS` 再切换，避免生产/客服两套表头不一致。

## 相关文件

- `dimoldb_store.py` — `LEGACY_IMPORT_HEADERS`、`effective_dims` 仅读长宽高
- `app_production.py` — 模板/导出/导入 7 列
- `scripts/import_dimoldb_7col.py` — 服务器命令行覆盖导入
- `docs/dimoldb-cleanup-handoff.md` — 重复/无 code 数据清理（导入稳定后再做）
