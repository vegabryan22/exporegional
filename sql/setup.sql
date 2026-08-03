CREATE DATABASE IF NOT EXISTS exporegional
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'exporegional_user'@'localhost' IDENTIFIED BY 'exporegional123';
GRANT ALL PRIVILEGES ON exporegional.* TO 'exporegional_user'@'localhost';
FLUSH PRIVILEGES;

