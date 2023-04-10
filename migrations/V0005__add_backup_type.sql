CREATE TYPE service.backup_type AS ENUM (
	'nas',
	's3'
);

ALTER TABLE service.backups ADD COLUMN type service.backup_type NOT NULL DEFAULT 'nas';
ALTER TABLE service.backups ALTER COLUMN type DROP DEFAULT;
