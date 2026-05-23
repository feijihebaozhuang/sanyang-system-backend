-- 商家编码 51714：外径 26×26×12 正方形（订单文本 22*10;长度26cm 易误解析，以映射为准）
INSERT INTO km_sku_map
  (outer_id, spec_alias, product_type, length, width, height, dim_kind, material, km_title)
VALUES
  ('51714', '26×26×12 白色W7W 外径', 'zhengsquare', 26, 26, 12, 'outer', '白色W7W', '')
ON DUPLICATE KEY UPDATE
  spec_alias=VALUES(spec_alias),
  product_type=VALUES(product_type),
  length=VALUES(length),
  width=VALUES(width),
  height=VALUES(height),
  dim_kind=VALUES(dim_kind),
  material=VALUES(material);
