# 快麦子单 `platformSpec` 字段说明

## 常见结构（天猫小批量等）

快麦 API 子单上 `platformSpec` 常为 **JSON 字符串**，解析后为数组，每项 `name` + `value`：

```json
[
  {"name": "数量", "value": "【100个】"},
  {"name": "长度", "value": "28cm"},
  {"name": "宽", "value": "15cm"},
  {"name": "高", "value": "6cm"},
  {"name": "颜色", "value": "白色"}
]
```

系统入库时由 `km_platform_spec_json_to_attrs()` 拼成：

```text
数量:【100个】；长度:28cm；宽:15cm；高:6cm；颜色:白色
```

再与 `skuPropertiesName`（如 `【100个】长度【28cm】；高【6cm】`）**合并，只增不减**，避免接口文本缺宽。

## 与界面差异

| 来源 | 示例 |
|------|------|
| 快麦后台界面 | `【100个】长度【28cm】；宽【15cm】高【6cm】白色` |
| `skuPropertiesName`（API） | 可能只有 `【100个】长度【28cm】；高【6cm】` |
| `platformSpec`（JSON） | 常有独立的 `宽:15cm` |

因此打单逻辑 **优先解析 `platformSpec` JSON**，再补 `skuPropertiesName`。

## 服务器上查看某一单（如 28272）

在项目根目录（已配置 `km_token.json`）：

```bash
python scripts/km_dump_line_spec.py --sid 28272
```

输出含 `platformSpec_raw`（原始 JSON）、`platformSpec_parsed`、`collect_attrs`、`display`。
