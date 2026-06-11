import re

s = '宽【10cm】高【2cm】【内径】;【100个】长度【11cm【内径】】'

# 直接从高度后面开始测试
h_end = '高【2cm】【内径】;【100个】长度【11cm【内径】】'

# 尝试匹配长部分
# 完整字符串从高度后开始
m = re.search(r'(?:长度?)', '长度【11cm')
print(f'(?:长度?) on "长度【11cm": {m}')

m2 = re.search(r'(?:长度?)[【\[]', '长度【11cm')
print(f'(?:长度?)[【\[] on "长度【11cm": {m2}')

# 看整体正则哪里卡住
# 使用更简单的方式
tail = ';【100个】长度【11cm【内径】】'
m3 = re.search(r'(?:长度?)[【\[]\s*([\d.]+)\s*(\w*)\s*[】\]]', tail)
print(f'长部分正则 on tail: {m3}')
if m3:
    print(f'  值={m3.group(1)}, 单位={m3.group(2)!r}')
else:
    # 最后[】\]]尝试不同方式
    m4 = re.search(r'(?:长度?)[【\[]\s*([\d.]+)\s*(\w*).*?[】\]]', tail)
    print(f'用.*?代替\\s*: {m4}')
    if m4:
        print(f'  值={m4.group(1)}, 单位={m4.group(2)!r}')
