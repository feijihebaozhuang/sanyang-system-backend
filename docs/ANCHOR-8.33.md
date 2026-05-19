# 备份锚点 v8.33（小马）

> **锚点日期**：2026-05-19  
> **Git 标签**：`v8.33`  
> **分支**：`main`  
> **说明**：客服端 + 生产端双系统当前可运行状态的完整代码锚点，便于以后回滚或对照。

## 包含的两个系统

| 系统 | 入口 | 前端 | 端口 |
|------|------|------|------|
| 客服端 | `app_cs.py` | `index_cs.html` | 3001 |
| 生产端 | `app_production.py` | `index.html` | 3002 |

## 本锚点已稳定的功能（摘要）

- 买家下单 SKU 属性展示（不读商品标题做规格/分类/定制判定）
- 打单管理：生产规格（尺寸蓝、材料紫、颜色橙、数量置后加大）
- 生产材料关键词映射、订单同步（快麦 + 1688）
- 飞机盒/纸箱等分类按属性识别

## 恢复到此锚点

```bash
# 代码回滚（服务器 repo 目录）
cd /www/feijihe/repo
git fetch origin --tags
git checkout v8.33
./deploy.sh
```

```powershell
# 本地 Windows
cd D:\Desktop\sanyang-system
git fetch origin --tags
git checkout v8.33
```

回滚后需在两端各执行一次 **强制同步订单**（`POST /api/sync/force`）。

## 服务器数据备份（与代码锚点配合）

代码锚点 **不包含** 服务器上的 `data.json`、`orders_cache.json`、`.env`、`km_token.json` 等（未进 Git）。  
请在服务器执行：

```bash
cd /www/feijihe/repo
./scripts/backup-anchor.sh 8.33
```

会在 `/home/admin/backup/feijihe/anchor/` 生成带版本号的代码包，并提示备份 stable 目录下的数据文件。

## 查看锚点对应提交

```bash
git show v8.33 --no-patch
```
