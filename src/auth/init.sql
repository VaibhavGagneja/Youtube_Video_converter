-- init.sql
-- Note: The database and user are created automatically by
-- Docker MySQL via MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE env vars.
-- This script only creates tables and seeds data.

CREATE TABLE IF NOT EXISTS user (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL
);

INSERT IGNORE INTO user (email, password) VALUES ('georgio@email.com', 'Admin123');

