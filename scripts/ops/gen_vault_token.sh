#!/bin/bash
# 生成 permission_vault 用随机 Token（应用机与 156 共用同一串）
openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))"
