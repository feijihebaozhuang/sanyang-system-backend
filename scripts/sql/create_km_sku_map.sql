-- 快麦商家编码 → 生产规格映射（轻量层）
-- 用法: mysql -u ... sanyang < scripts/sql/create_km_sku_map.sql

CREATE TABLE IF NOT EXISTS `km_sku_map` (
  `outer_id` VARCHAR(128) NOT NULL COMMENT '商家编码/outerId',
  `spec_alias` VARCHAR(512) NOT NULL DEFAULT '' COMMENT '规格别名（生产解析用）',
  `product_type` VARCHAR(64) NOT NULL DEFAULT '' COMMENT 'zhengsquare/juxing/...',
  `length` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `width` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `height` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `dim_kind` VARCHAR(16) NOT NULL DEFAULT '' COMMENT 'inner/outer/空',
  `material` VARCHAR(128) NOT NULL DEFAULT '',
  `km_title` VARCHAR(256) NOT NULL DEFAULT '' COMMENT '快麦简称，仅展示',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`outer_id`),
  KEY `idx_spec_alias` (`spec_alias`(191)),
  KEY `idx_dims` (`product_type`, `length`, `width`, `height`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='快麦商家编码生产映射';
