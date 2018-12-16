CREATE SCHEMA service;

CREATE TABLE service.backups (
  id BIGSERIAL PRIMARY KEY,
  path text NOT NULL,
  provenance text NOT NULL,
  aspect_ratio_x bigint NOT NULL,
  aspect_ratio_y bigint NOT NULL,
  image_size_x bigint NOT NULL,
  image_size_y bigint NOT NULL,
  note text NOT NULL
);
