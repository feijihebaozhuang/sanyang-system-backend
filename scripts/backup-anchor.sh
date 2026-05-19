#!/bin/bash
# 双系统备份锚点：打 Git 标签对应的代码包 + stable 运行时数据（客服 3001 / 生产 3002）
# 用法: ./scripts/backup-anchor.sh [版本号]   例: ./scripts/backup-anchor.sh 8.33
set -euo pipefail

VERSION="${1:-8.33}"
TAG="v${VERSION}"
REPO_DIR="${REPO_DIR:-/www/feijihe/repo}"
STABLE_DIR="${STABLE_DIR:-/www/feijihe/stable}"
BACKUP_ROOT="${BACKUP_ROOT:-/home/admin/backup/feijihe/anchor}"
STAMP=$(date +%Y%m%d_%H%M%S)
DEST="${BACKUP_ROOT}/${TAG}_${STAMP}"

mkdir -p "$DEST"

echo "=== 三羊双系统备份锚点 ${TAG}（小马） ==="
echo "目标目录: $DEST"

cd "$REPO_DIR"
git fetch origin --tags 2>/dev/null || true
COMMIT=$(git rev-parse "${TAG}" 2>/dev/null || git rev-parse HEAD)
echo "提交: $COMMIT"

# 1) 与标签一致的源码归档（不含 .git）
git archive --format=tar.gz -o "${DEST}/code_${TAG}.tar.gz" "$COMMIT"
echo "  [OK] code_${TAG}.tar.gz"

# 2) stable 运行时数据（未进 Git 的配置与缓存）
DATA_FILES=(
  data.json
  orders_cache.json
  dimoldb.json
  inventory.json
  quote_data.json
  permission_data.json
  printed_orders.json
)
mkdir -p "${DEST}/stable_data"
for f in "${DATA_FILES[@]}"; do
  if [ -f "${STABLE_DIR}/${f}" ]; then
    cp "${STABLE_DIR}/${f}" "${DEST}/stable_data/"
    echo "  [OK] stable_data/${f}"
  fi
done
for f in .env km_token.json alibaba_shops.json; do
  if [ -f "${STABLE_DIR}/${f}" ]; then
    cp "${STABLE_DIR}/${f}" "${DEST}/stable_data/"
    echo "  [OK] stable_data/${f} (敏感，请妥善保管)"
  fi
done

# 3) 记录元信息
cat > "${DEST}/ANCHOR.txt" <<EOF
锚点版本: ${TAG}
备份时间: $(date '+%Y-%m-%d %H:%M:%S')
Git 提交: ${COMMIT}
客服端: app_cs.py :3001
生产端: app_production.py :3002
恢复代码: cd ${REPO_DIR} && git checkout ${TAG} && ./deploy.sh
EOF

tar -czf "${BACKUP_ROOT}/${TAG}_${STAMP}_full.tar.gz" -C "${BACKUP_ROOT}" "$(basename "$DEST")"
echo ""
echo "完成:"
echo "  目录: ${DEST}"
echo "  整包: ${BACKUP_ROOT}/${TAG}_${STAMP}_full.tar.gz"
echo "Git 标签 ${TAG} 需在 repo 中已存在: git tag -l '${TAG}'"
