# Скрипт для запуска синхронизации Bitrix24 через cron (Task Scheduler в Windows)
# Использование: настройте задачу в Планировщике задач Windows для запуска этого скрипта

# Получаем директорию, где находится скрипт
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# Переходим в корневую директорию проекта
Set-Location $ProjectDir

# Запускаем синхронизацию через docker-compose
docker-compose exec -T bitrix-sync python /app/bitrix-sync/cli.py

# Альтернативный вариант, если контейнер не запущен:
# docker-compose run --rm bitrix-sync python /app/bitrix-sync/cli.py
