#!/bin/bash

# Скрипт для сборки и публикации Docker образа в приватный реестр
# Использование: ./build-and-push.sh [registry-url] [image-name] [tag]

set -e

# Параметры по умолчанию
REGISTRY="${1:-your-registry.com}"
IMAGE_NAME="${2:-telegram_miniapp}"
TAG="${3:-latest}"

# Полное имя образа с реестром
FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${TAG}"

echo "========================================="
echo "Сборка и публикация Docker образа"
echo "========================================="
echo "Реестр: ${REGISTRY}"
echo "Имя образа: ${IMAGE_NAME}"
echo "Тег: ${TAG}"
echo "Полное имя: ${FULL_IMAGE_NAME}"
echo "========================================="
echo ""

# Шаг 1: Сборка образа
echo "Шаг 1: Сборка Docker образа..."
docker build -t "${IMAGE_NAME}:${TAG}" -t "${FULL_IMAGE_NAME}" .
echo "✓ Образ собран успешно"
echo ""

# Шаг 2: Вход в реестр (опционально)
echo "Шаг 2: Вход в Docker Registry..."
echo "Если требуется аутентификация, введите учетные данные."
echo "Для пропуска нажмите Enter..."
read -p "Введите команду для входа (например: docker login ${REGISTRY}): " LOGIN_CMD

if [ ! -z "$LOGIN_CMD" ]; then
    eval "$LOGIN_CMD"
    if [ $? -eq 0 ]; then
        echo "✓ Успешный вход в реестр"
    else
        echo "✗ Ошибка входа в реестр"
        exit 1
    fi
else
    echo "→ Вход пропущен"
fi
echo ""

# Шаг 3: Публикация образа
echo "Шаг 3: Публикация образа в реестр..."
docker push "${FULL_IMAGE_NAME}"
if [ $? -eq 0 ]; then
    echo "✓ Образ успешно опубликован: ${FULL_IMAGE_NAME}"
else
    echo "✗ Ошибка публикации образа"
    exit 1
fi
echo ""

echo "========================================="
echo "Готово! Образ доступен по адресу:"
echo "${FULL_IMAGE_NAME}"
echo "========================================="

