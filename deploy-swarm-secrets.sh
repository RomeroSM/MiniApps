#!/bin/bash

# Скрипт для развертывания с Docker Secrets

set -e

STACK_NAME="telegram-miniapp"
COMPOSE_FILE="docker-stack.yml"

echo "🔐 Развертывание Telegram Mini App с Docker Secrets..."

# Проверка, что мы в Swarm режиме
if ! docker info | grep -q "Swarm: active"; then
    echo "❌ Docker Swarm не инициализирован!"
    echo "Выполните: docker swarm init"
    exit 1
fi

# Создание secrets (если не существуют)
echo "🔑 Создание secrets..."

if ! docker secret ls | grep -q "mysql_root_password"; then
    read -sp "Введите MySQL root пароль: " MYSQL_ROOT_PASS
    echo ""
    echo "$MYSQL_ROOT_PASS" | docker secret create mysql_root_password -
    echo "✅ mysql_root_password создан"
else
    echo "ℹ️  mysql_root_password уже существует"
fi

if ! docker secret ls | grep -q "mysql_user"; then
    read -p "Введите MySQL пользователя [appuser]: " MYSQL_USER
    MYSQL_USER=${MYSQL_USER:-appuser}
    echo "$MYSQL_USER" | docker secret create mysql_user -
    echo "✅ mysql_user создан"
else
    echo "ℹ️  mysql_user уже существует"
fi

if ! docker secret ls | grep -q "mysql_password"; then
    read -sp "Введите MySQL пароль: " MYSQL_PASS
    echo ""
    echo "$MYSQL_PASS" | docker secret create mysql_password -
    echo "✅ mysql_password создан"
else
    echo "ℹ️  mysql_password уже существует"
fi

if ! docker secret ls | grep -q "secret_key"; then
    read -sp "Введите Flask SECRET_KEY: " SECRET_KEY
    echo ""
    echo "$SECRET_KEY" | docker secret create secret_key -
    echo "✅ secret_key создан"
else
    echo "ℹ️  secret_key уже существует"
fi

if ! docker secret ls | grep -q "telegram_bot_token"; then
    read -sp "Введите Telegram Bot Token: " BOT_TOKEN
    echo ""
    echo "$BOT_TOKEN" | docker secret create telegram_bot_token -
    echo "✅ telegram_bot_token создан"
else
    echo "ℹ️  telegram_bot_token уже существует"
fi

# Проверка наличия образа
if ! docker images | grep -q "telegram_miniapp"; then
    echo "📦 Сборка образа..."
    docker build -t telegram_miniapp:latest .
else
    echo "✅ Образ telegram_miniapp:latest уже существует"
fi

# Развертывание stack
echo "📤 Развертывание stack..."
docker stack deploy -c $COMPOSE_FILE $STACK_NAME

# Ожидание запуска сервисов
echo "⏳ Ожидание запуска сервисов..."
sleep 5

# Проверка статуса
echo "📊 Статус сервисов:"
docker stack services $STACK_NAME

echo ""
echo "✅ Развертывание завершено!"
echo ""
echo "Полезные команды:"
echo "  docker stack services $STACK_NAME  - список сервисов"
echo "  docker service logs -f ${STACK_NAME}_web  - логи веб-сервиса"
echo "  docker secret ls  - список secrets"

