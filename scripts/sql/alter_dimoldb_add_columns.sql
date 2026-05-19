-- 刀模库 dimoldb 补列（执行一次；列已存在会报错可忽略）
-- 应用启动时 dimoldb_store.ensure_dimoldb_schema 也会自动补列

ALTER TABLE dimoldb ADD COLUMN code VARCHAR(64) NOT NULL DEFAULT '' COMMENT '编码';
ALTER TABLE dimoldb ADD COLUMN production_spec VARCHAR(512) NOT NULL DEFAULT '' COMMENT '生产规格';
ALTER TABLE dimoldb ADD COLUMN km_mapping_code VARCHAR(128) NOT NULL DEFAULT '' COMMENT '快麦商品映射';
