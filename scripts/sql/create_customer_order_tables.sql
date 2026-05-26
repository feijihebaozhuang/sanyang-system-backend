-- 三羊客户下单系统 — 5 张业务表（与 order_cache_* / km_sku_map 同库 sanyang）
-- 用法: mysql -u ... sanyang < scripts/sql/create_customer_order_tables.sql

CREATE TABLE IF NOT EXISTS `co_admin_user` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(64) NOT NULL COMMENT '登录账号',
  `password_hash` CHAR(64) NOT NULL COMMENT 'SHA256',
  `display_name` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '显示名',
  `role` VARCHAR(32) NOT NULL DEFAULT 'viewer' COMMENT 'admin/viewer',
  `enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='3003 后台管理员';

CREATE TABLE IF NOT EXISTS `co_product_category` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(64) NOT NULL COMMENT '产品类型码 zhengsquare/koudi/...',
  `name` VARCHAR(128) NOT NULL COMMENT '展示名 飞机盒/扣底盒',
  `sort_order` INT NOT NULL DEFAULT 0,
  `spec_fields_json` JSON NULL COMMENT '规格字段配置 length/width/height/material/dim_kind',
  `enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `remark` VARCHAR(512) NOT NULL DEFAULT '',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`),
  KEY `idx_sort` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品目录分类';

CREATE TABLE IF NOT EXISTS `co_cs_staff` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `employee_name` VARCHAR(64) NOT NULL COMMENT '姓名',
  `phone` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '微信同号（手机号）',
  `wx_openid` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '客服小程序绑定的微信openid',
  `enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `remark` VARCHAR(512) NOT NULL DEFAULT '',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_employee_name` (`employee_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客服员工（小程序阶段用）';

CREATE TABLE IF NOT EXISTS `co_customer` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(128) NOT NULL COMMENT '客户名/公司简称',
  `contact_name` VARCHAR(64) NOT NULL DEFAULT '',
  `phone` VARCHAR(32) NOT NULL DEFAULT '',
  `company` VARCHAR(256) NOT NULL DEFAULT '',
  `assigned_cs_id` INT UNSIGNED NULL COMMENT '归属客服 co_cs_staff.id',
  `wx_openid` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '小程序 openid',
  `status` VARCHAR(32) NOT NULL DEFAULT 'active' COMMENT 'active/disabled',
  `remark` VARCHAR(512) NOT NULL DEFAULT '',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_assigned_cs` (`assigned_cs_id`),
  KEY `idx_phone` (`phone`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='B2B 客户';

CREATE TABLE IF NOT EXISTS `co_order` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `order_no` VARCHAR(32) NOT NULL COMMENT '业务单号 COyyyyMMddHHmmss',
  `customer_id` INT UNSIGNED NOT NULL,
  `cs_staff_id` INT UNSIGNED NULL COMMENT '接单客服',
  `product_category_code` VARCHAR(64) NOT NULL DEFAULT '',
  `length` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `width` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `height` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `material` VARCHAR(128) NOT NULL DEFAULT '',
  `dim_kind` VARCHAR(16) NOT NULL DEFAULT 'outer' COMMENT 'inner/outer',
  `outer_id` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '匹配 km_sku_map.outer_id',
  `qty` INT NOT NULL DEFAULT 0,
  `unit_price` DECIMAL(14,4) NOT NULL DEFAULT 0,
  `total_price` DECIMAL(14,2) NOT NULL DEFAULT 0,
  `status` VARCHAR(32) NOT NULL DEFAULT 'draft' COMMENT 'draft/pending_review/approved/rejected/in_production/completed/cancelled',
  `remark` VARCHAR(1024) NOT NULL DEFAULT '',
  `created_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT 'admin/customer/cs',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_customer` (`customer_id`),
  KEY `idx_cs` (`cs_staff_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created` (`created_at`),
  KEY `idx_dims` (`product_category_code`, `length`, `width`, `height`, `material`(64))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户下单订单';
