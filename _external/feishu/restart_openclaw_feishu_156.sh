#!/bin/bash
# 在 156 权限机执行：重启 OpenClaw 网关（飞书长连接）
set -euo pipefail

echo "==> 监听端口"
ss -tlnp | grep -E '18789|18900|8788' || echo "(无监听)"

echo "==> 尝试重启 OpenClaw"
if systemctl list-unit-files 2>/dev/null | grep -qi openclaw; then
  sudo systemctl restart openclaw || sudo systemctl restart openclaw-gateway
  systemctl status openclaw --no-pager 2>/dev/null | head -10 || \
    systemctl status openclaw-gateway --no-pager 2>/dev/null | head -10
elif command -v openclaw &>/dev/null; then
  openclaw gateway restart || true
else
  echo "未找到 openclaw systemd/命令，请手动："
  echo "  ps aux | grep -i openclaw"
  echo "  或查看 ~/.openclaw/ 与 nohup/screen 进程"
fi

echo ""
echo "==> 本机 MCP/网关探活"
curl -sk -o /dev/null -w "18789 → %{http_code}\n" https://127.0.0.1:18789/mcp --connect-timeout 5 2>/dev/null || true

echo ""
echo "飞书后台应选「长连接」，不是 HTTP 填 213/87 地址。"
echo "156 安全组出站默认放行即可；入站 18789 仅 Cursor MCP 用，与飞书收消息无关。"
