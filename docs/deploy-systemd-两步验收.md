# 部署验收：systemd + 报价 keywords（两步）

## 第一步：systemd 使用 venv 的 Python（服务器 root 执行一次）

`ExecStart` 必须指向 stable 目录下的 venv，否则 `cryptography` 等依赖装不上会导致 MySQL 连不上。

```bash
# 方式 A：仓库自带单元（推荐，路径已写好）
cd /www/feijihe/repo
sudo bash deploy/install-systemd.sh

# 方式 B：手工改两行后 reload
sudo nano /etc/systemd/system/sanyang-cs.service
# ExecStart=/www/feijihe/stable/venv/bin/python3 app_cs.py

sudo nano /etc/systemd/system/sanyang-production.service
# ExecStart=/www/feijihe/stable/venv/bin/python3 app_production.py

sudo systemctl daemon-reload
sudo systemctl enable sanyang-cs sanyang-production
sudo systemctl restart sanyang-cs sanyang-production
```

验收：

```bash
systemctl status sanyang-cs sanyang-production
ss -tlnp | grep -E '3001|3002'
# 应看到 venv/bin/python3，而非系统 python3
```

之后日常发版只需：

```bash
cd /www/feijihe/repo && git pull && ./deploy.sh
```

`deploy.sh` 若检测到 systemd 单元存在，会自动 `systemctl restart`，不再用 nohup 抢端口。

## 第二步：报价参数保存一次（浏览器）

1. 登录 **客服端**（3001）或有权「权限管理」的账号  
2. 打开 **报价参数编辑**  
3. 确认 `material_mapping` 每条有 **keywords**（纸箱类应有 `五层,EB,B坑` 等）  
4. 点 **保存** → 写入 MySQL `quote_config`  

生产端打单页再 **刷新缓存**（`refresh=1` 或点搜索）。

---

就这两步。代码已在 `main`（含 `cryptography`、红线固定倍率、缺料文案、keywords 自动补全）。
