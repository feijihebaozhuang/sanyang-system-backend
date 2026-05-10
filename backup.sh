#!/bin/bash
# 三羊包装生产管理系统 - 完整数据备份脚本
# 每天凌晨4点执行，由crontab调用

APP_DIR="/www/wwwroot/feijihe"
BACKUP_DIR="/home/admin/backup/feijihe"
DATE=$(date +%Y%m%d)

# 确保备份目录存在
mkdir -p "$BACKUP_DIR"

# 1. 备份核心数据文件 data.json（最关键的）
cp "$APP_DIR/data.json" "$BACKUP_DIR/data_${DATE}.json"

# 2. 全量项目备份（包含所有代码）
tar -czf "$BACKUP_DIR/feijihe_full_${DATE}.tar.gz" \
    -C "$(dirname $APP_DIR)" \
    "$(basename $APP_DIR)/app.py" \
    "$(basename $APP_DIR)/index.html" \
    "$(basename $APP_DIR)/data.json" \
    "$(basename $APP_DIR)/keepalive.sh" 2>/dev/null

# 3. 额外备份到第二个位置（双重保险）
cp "$APP_DIR/data.json" "/tmp/data_${DATE}_emergency.json"

# 4. 清理30天前的旧备份
find "$BACKUP_DIR" -name "*.json" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份完成: data_${DATE}.json + feijihe_full_${DATE}.tar.gz"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 数据大小: $(wc -c < "$APP_DIR/data.json") bytes"
