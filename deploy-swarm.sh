#!/bin/bash

# Скрипт для быстрого развертывания в Docker Swarm

set -e

STACK_NAME="telegram-miniapp"
COMPOSE_FILE="docker-compose.swarm.yml"

echo "🚀 Развертывание Telegram Mini App в Docker Swarm..."

# Проверка, что мы в Swarm режиме
if ! docker info | grep -q "Swarm: active"; then
    echo "❌ Docker Swarm не инициализирован!"
    echo "Выполните: docker swarm init"
    exit 1
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
echo "  docker service logs -f ${STACK_NAME}_db  - логи БД"
echo "  docker stack ps $STACK_NAME  - статус задач"
echo "  docker stack rm $STACK_NAME  - удаление stack"

