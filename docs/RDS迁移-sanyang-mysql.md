# 213 → 阿里云 RDS 迁移（sanyang-mysql）

> **执行人**：小马哥（87 应用机 + RDS 控制台）  
> **老板侧**：RDS 已购买，**勿在未验收前改生产 `.env`**  
> **代码**：迁移脚本 `scripts/ops/migrate_mysql_to_rds.sh`（`main` 已 push）

---

## 一、RDS 实例信息（2026-05-29 已创建）

| 项 | 值 |
|----|-----|
| 实例 ID | `rm-7xv9u0s6tr3e24tg6` |
| 名称 | `sanyang-mysql` |
| 地域 / 可用区 | 华南3（广州）可用区 B |
| 引擎 | MySQL 8.0（基础系列，2核4G，100G 高性能云盘） |
| 网络 | 专有网络（须与 **87 应用机同 VPC**） |
| 端口 | 3306 |
| 计费 | 包年包月至 2027-05-30 |
| 存储自动扩展 | 已开启 |

**内网连接地址**（以控制台「查看连接详情」为准，一般为）：

```text
rm-7xv9u0s6tr3e24tg6.mysql.rds.aliyuncs.com
```

---

## 二、迁移前：RDS 控制台配置（约 10 分钟）

### 2.1 创建数据库

| 项 | 值 |
|----|-----|
| 库名 | `sanyang` |
| 字符集 | `utf8mb4` |
| 排序规则 | `utf8mb4_unicode_ci`（或默认） |

### 2.2 创建账号

| 项 | 值 |
|----|-----|
| 账号 | `sanyang_app` |
| 密码 | 强密码（记入 87 `stable/.env`，勿提交 Git） |
| 权限 | 对 `sanyang` 库 **读写**（SELECT/INSERT/UPDATE/DELETE） |

### 2.3 白名单

| 阶段 | 允许 IP |
|------|---------|
| 迁移期间 | **87 应用机内网 IP** + **213 内网 IP**（`172.19.18.36` 或 213 ECS 内网） |
| 迁移完成验收后 | **仅保留 87 内网 IP**，删除 213 |

### 2.4 备份策略（建议）

- **自动备份**：开启，保留 **7 天**
- **释放实例后备份**：**保留最后一个**

---

## 三、迁移前：连通性测试（87 上）

SSH **8.166.132.87**，确认能连 RDS（**尚未改 `.env`** 时用 `-h` 手动测）：

```bash
mysql -h rm-7xv9u0s6tr3e24tg6.mysql.rds.aliyuncs.com -P 3306 -u sanyang_app -p -e "SELECT 1 AS ok;"
```

返回 `ok = 1` 再继续。

若失败，检查：VPC 是否一致、白名单、账号密码、安全组。

---

## 四、正式迁移（建议凌晨，停机窗口 15～30 分钟）

### 4.1 迁移前（87）

```bash
cd /www/feijihe/repo && git pull origin main && ./deploy.sh
```

可选：通知业务低峰操作；迁移期间订单同步可能短暂写旧库。

### 4.2 方式 A：脚本（推荐）

在 **87** 上（能同时访问 213 与 RDS）：

```bash
cd /www/feijihe/stable

export SOURCE_HOST=172.19.18.36
export SOURCE_USER=sanyang_app
export SOURCE_DB=sanyang
export RDS_HOST=rm-7xv9u0s6tr3e24tg6.mysql.rds.aliyuncs.com
export RDS_USER=sanyang_app
export RDS_DB=sanyang

bash scripts/ops/migrate_mysql_to_rds.sh
```

按提示输入：**213 源库密码** → **RDS 目标库密码**。

### 4.3 方式 B：手工

```bash
STAMP=$(date +%Y%m%d_%H%M)
DUMP="/tmp/sanyang_to_rds_${STAMP}.sql.gz"

mysqldump -h 172.19.18.36 -u sanyang_app -p \
  --single-transaction --routines --triggers --events \
  sanyang | gzip > "$DUMP"

gunzip -t "$DUMP"
ls -lh "$DUMP"

gunzip -c "$DUMP" | mysql -h rm-7xv9u0s6tr3e24tg6.mysql.rds.aliyuncs.com -u sanyang_app -p sanyang
```

**备份文件保留**：`scp` 或拷到 `/home/admin/backup/`，确认无误后再删 213。

---

## 五、迁移后：数据验收（RDS 上）

```bash
mysql -h rm-7xv9u0s6tr3e24tg6.mysql.rds.aliyuncs.com -u sanyang_app -p sanyang
```

```sql
SHOW TABLES;
SELECT COUNT(*) AS dimoldb FROM dimoldb;              -- 期望约 18000+
SELECT COUNT(*) AS orders FROM order_cache_orders;
SELECT COUNT(*) AS km_sku FROM km_sku_map;
SELECT COUNT(*) AS items FROM order_cache_items;
```

**与 213 迁移前条数一致** 再切生产。

213 上迁移前可先记数：

```bash
mysql -h 172.19.18.36 -u sanyang_app -p sanyang -e \
  "SELECT COUNT(*) dimoldb FROM dimoldb; SELECT COUNT(*) orders FROM order_cache_orders;"
```

---

## 六、切换生产（仅改 `.env`）

编辑 **87** `/www/feijihe/stable/.env`：

```env
MYSQL_HOST=rm-7xv9u0s6tr3e24tg6.mysql.rds.aliyuncs.com
MYSQL_PORT=3306
MYSQL_USER=sanyang_app
MYSQL_PASSWORD=<RDS 新密码>
MYSQL_DATABASE=sanyang
```

重启三端：

```bash
sudo systemctl restart sanyang-cs sanyang-production sanyang-customer-order
```

运行验收：

```bash
bash /www/feijihe/stable/scripts/ops/verify_production.sh
```

### 浏览器验收清单

| 功能 | 地址 | 期望 |
|------|------|------|
| 生产打单 | https://feijihe.top | 订单列表、刀模正常 |
| 客服报价 | https://zean.feijihe.top | 报价、权限正常 |
| 客户下单 | 3003 / 小程序 | 审单、推快麦正常 |
| 快麦订单同步 | 生产端订单 | 增量同步无 MySQL 报错 |

---

## 七、切换后清理

1. **RDS 白名单**：删除 213 IP，仅留 87  
2. **观察 3～7 天**：无异常再处理 213  
3. **213 ECS**：确认无业务依赖后 **退订**（原 8 月到期，可提前）  
4. **213 禁止**：不要再跑 Flask；MySQL 可停，仅留备份文件

---

## 八、回滚（仅当切换后出大问题）

1. `.env` 改回 `MYSQL_HOST=172.19.18.36`（213）  
2. `systemctl restart` 三端  
3. 213 MySQL 仍在且数据未删时可立即恢复；若已删 213，用迁移前 `mysqldump` 恢复

**因此：切换前务必保留 `/tmp/sanyang_to_rds_*.sql.gz` 副本。**

---

## 九、相关文件

| 文件 | 说明 |
|------|------|
| `scripts/ops/migrate_mysql_to_rds.sh` | 一键导出 213 → 导入 RDS |
| `scripts/ops/backup_mysql_213_for_reinstall.sh` | 213 全库备份（重装前） |
| `scripts/ops/mysql_daily_backup_213.sh` | 213 日备（切换前仍可用） |
| `scripts/ops/verify_production.sh` | 应用机验收 |
| `docs/三机部署方案-小马哥.md` | 第十章架构说明 |

---

## 十、常见问题

**Q：87 连不上 RDS？**  
同 VPC、RDS 白名单含 87 内网 IP、用 **内网地址** 而非公网地址。

**Q：导入报字符集错误？**  
建库时用 `utf8mb4`；dump 前 213 库已是 utf8mb4 一般无问题。

**Q：切换后快麦订单不同步？**  
与 MySQL 主机无关，查 `km_token.json`、systemd timer `sanyang-km-sync.timer`。

**Q：deploy.sh 会覆盖 `.env` 吗？**  
不会。`deploy.sh` 不同步 `.env`，只改 `.env` 后 restart 即可。
