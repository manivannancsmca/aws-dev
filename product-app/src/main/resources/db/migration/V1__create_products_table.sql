-- Flyway migration V1: initial schema for the product-app.
-- Flyway runs this file exactly once per database and records it in flyway_schema_history.
-- NEVER edit this file after it has been applied; create V2__... for further changes.

CREATE TABLE products (
    id          BIGINT         NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100)   NOT NULL,
    description VARCHAR(500)   NULL,
    price       DECIMAL(10, 2) NOT NULL,
    quantity    INT            NOT NULL DEFAULT 0,
    created_at  DATETIME(6)    NOT NULL,
    updated_at  DATETIME(6)    NOT NULL,
    PRIMARY KEY (id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci;

CREATE INDEX idx_products_name ON products (name);
