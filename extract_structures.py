# -*- coding: utf-8 -*-
"""从 JSONL 对话记录中提取用户发的结构文本段落"""
import json, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

jsonl_path = r'C:\Users\Administrator\.cursor\projects\d-Desktop-sanyang-system\agent-transcripts\b134fd39-b868-43d8-9077-ec27eae3f1c9\b134fd39-b868-43d8-9077-ec27eae3f1c9.jsonl'

with open(jsonl_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"总行数: {len(lines)}")

# 提取所有包含 ═══ 的用户消息
user_msgs_with_structure = []
for i, line in enumerate(lines):
    line = line.strip()
    if not line:
        continue
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        continue
    
    if data.get('role') != 'user':
        continue
    
    content = data.get('message', {}).get('content', [])
    text = ''
    if isinstance(content, list):
        for c in content:
            if c.get('type') == 'text':
                text += c.get('text', '')
    elif isinstance(content, str):
        text = content
    else:
        text = str(content)
    
    if '═══' in text:
        user_msgs_with_structure.append((i+1, text))

print(f"\n找到 {len(user_msgs_with_structure)} 条含 ═══ 的用户消息\n")

for idx, (line_num, text) in enumerate(user_msgs_with_structure):
    print(f"{'='*80}")
    print(f"消息 #{idx+1} (JSONL 第 {line_num} 行)")
    print(f"{'='*80}")
    print(text)
    print()
