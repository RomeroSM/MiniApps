#!/bin/bash
# Скрипт для запуска синхронизации Bitrix24 через cron
# Использование: добавьте в crontab: 0 0 * * * /path/to/sync-cron.sh

# Получаем директорию, где находится скрипт
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Переходим в корневую директорию проекта
cd "$PROJECT_DIR" || exit 1

# Запускаем синхронизацию через docker-compose
docker-compose exec -T bitrix-sync python /app/bitrix-sync/cli.py

# Альтернативный вариант, если контейнер не запущен:
# docker-compose run --rm bitrix-sync python /app/bitrix-sync/cli.py
