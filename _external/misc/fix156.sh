#!/bin/bash
# 一键修复156 OpenClaw
# 1. 配SSH密钥
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIACf2ujdgrgGVjcgft7/tOKecjpMm2kaXn6aMV6D6LBi root@iZ7xv0aeodcpqg820gp3ebZ' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 2. 修复OpenClaw deepseek配置（补上API key）
cat /root/.openclaw/openclaw.json | python3 -c "
import json, sys
d = json.load(sys.stdin)

# 确保plugins.entries.deepseek有apiKey
plugins = d.setdefault('plugins', {}).setdefault('entries', {})
if 'deepseek' in plugins and not plugins['deepseek'].get('apiKey'):
    plugins['deepseek']['apiKey'] = 'sk-e89aaedba54a4a9fba79d61265abf58a'
    plugins['deepseek']['baseUrl'] = 'https://api.deepseek.com'
    print('已修复deepseek配置')
elif 'deepseek' not in plugins:
    plugins['deepseek'] = {
        'enabled': True,
        'apiKey': 'sk-e89aaedba54a4a9fba79d61265abf58a',
        'baseUrl': 'https://api.deepseek.com'
    }
    print('已添加deepseek配置')

# 也检查openai插件（可能用了它）
if 'openai' in plugins and not plugins['openai'].get('apiKey'):
    plugins['openai']['apiKey'] = 'sk-e89aaedba54a4a9fba79d61265abf58a'
    plugins['openai']['baseUrl'] = 'https://api.deepseek.com/v1'
    print('已修复openai配置指向deepseek')

with open('/root/.openclaw/openclaw.json', 'w') as f:
    json.dump(d, f, indent=2)
print('配置已保存')
"

# 3. 查看日志
echo '=== 最近日志 ==='
tail -30 /root/.openclaw/openclaw.log 2>/dev/null

# 4. 重启OpenClaw
systemctl restart openclaw
echo 'OpenClaw已重启'
sleep 3
systemctl status openclaw --no-pager -l | head -10
