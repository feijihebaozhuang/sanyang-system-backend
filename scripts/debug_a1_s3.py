import re

s = '宽【10cm】高【2cm】【内径】;【100个】长度【11cm【内径】】'

# 分段
m_w = re.search(r'宽[【\[]\s*([\d.]+)\s*(\w*)\s*[】\]]', s)
print(f'宽: {m_w} → {m_w.groups() if m_w else "None"}')

m_h = re.search(r'高[【\[]\s*([\d.]+)\s*(\w*)[^】]*[】\]]', s)
print(f'高: {m_h} → {m_h.groups() if m_h else "None"}')

m_l = re.search(r'(?:长度?)[【\[]\s*([\d.]+)\s*(\w*)\s*[】\]]', s)
print(f'长: {m_l} → {m_l.groups() if m_l else "None"}')

# 问题可能在 .*? 跨过 【内径】 时的匹配
# 整体用 debug
m = re.search(r'(宽[【\[]\s*([\d.]+)\s*(\w*)\s*[】\]])'
              r'(.*?)'
              r'(高[【\[]\s*([\d.]+)\s*(\w*)[^】]*[】\]])'
              r'(.*?)'
              r'((?:长度?)[【\[]\s*([\d.]+)\s*(\w*)\s*[】\]])', s)
if m:
    for i in range(1, 12):
        print(f'  group({i}): {m.group(i)!r}')
else:
    print('\n整体无匹配')
    # 试试不同的.*? 范围
    m2 = re.search(r'宽[【\[]\s*[\d.]+\s*\w*\s*[】\]].*?高[【\[]\s*[\d.]+\s*\w*.*?[】\]].*?长度?[【\[]\s*[\d.]+\s*\w*\s*[】\]]', s)
    print(f'简化版: {m2}')
