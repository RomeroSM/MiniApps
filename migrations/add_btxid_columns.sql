-- Миграция: Добавление колонки btxid во все справочные таблицы
-- Выполните этот скрипт для добавления колонок btxid в существующую базу данных

-- Добавление btxid в таблицу cities
ALTER TABLE cities 
ADD COLUMN btxid INT NULL DEFAULT NULL 
AFTER name;

-- Добавление btxid в таблицу objects
ALTER TABLE objects 
ADD COLUMN btxid INT NULL DEFAULT NULL 
AFTER name;

-- Добавление btxid в таблицу violation_categories
ALTER TABLE violation_categories 
ADD COLUMN btxid INT NULL DEFAULT NULL 
AFTER name;

-- Добавление btxid в таблицу violations
ALTER TABLE violations 
ADD COLUMN btxid INT NULL DEFAULT NULL 
AFTER name;

-- Добавление btxid в таблицу users
ALTER TABLE users 
ADD COLUMN btxid INT NULL DEFAULT NULL 
AFTER secret_key;
