#!/bin/bash
# 三羊系统测试快捷脚本
set -e
cd /www/feijihe/stable

echo "=============================="
echo " 三羊系统核心测试"
echo "=============================="
echo ""

python3 -m pytest tests/test_core.py -v --tb=short "$@"
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 全部通过"
else
    echo "❌ 有 $EXIT_CODE 个测试失败"
fi
exit $EXIT_CODE
