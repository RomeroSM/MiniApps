#!/bin/bash
# Скрипт для отправки образа в локальный Docker registry
# Использование: ./push-to-local.sh telegram-miniapp latest

set -e

IMAGE_NAME=${1:-"telegram-miniapp"}
TAG=${2:-"latest"}
REGISTRY=${3:-"localhost:5000"}

FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"
REGISTRY_IMAGE_NAME="${REGISTRY}/${FULL_IMAGE_NAME}"

echo "Тегирование образа: ${FULL_IMAGE_NAME} -> ${REGISTRY_IMAGE_NAME}"

# Проверка существования образа
if ! docker images "${FULL_IMAGE_NAME}" | grep -q "${IMAGE_NAME}"; then
    echo "Ошибка: Образ ${FULL_IMAGE_NAME} не найден!"
    echo "Доступные образы:"
    docker images
    exit 1
fi

# Тегирование
echo "Выполняется тегирование..."
docker tag "${FULL_IMAGE_NAME}" "${REGISTRY_IMAGE_NAME}"

# Отправка в registry
echo "Отправка образа в локальный registry: ${REGISTRY_IMAGE_NAME}"
docker push "${REGISTRY_IMAGE_NAME}"

if [ $? -eq 0 ]; then
    echo "Образ успешно отправлен в локальный registry!"
    echo "Используйте: docker pull ${REGISTRY_IMAGE_NAME}"
else
    echo "Ошибка при отправке образа!"
    echo "Убедитесь, что:"
    echo "  1. Registry запущен (docker-compose up -d)"
    echo "  2. Настроен insecure-registries в /etc/docker/daemon.json"
    exit 1
fi




