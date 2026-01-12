# Быстрый старт - Docker Swarm

## Минимальная инструкция для развертывания

### 1. Инициализация Swarm (один раз)

```bash
docker swarm init
```

### 2. Сборка образа

```bash
docker build -t telegram_miniapp:latest .
```

### 3. Создание .env файла (опционально)

```env
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_USER=appuser
MYSQL_PASSWORD=apppassword
MYSQL_DATABASE=telegram_miniapp
SECRET_KEY=your-secret-key
TELEGRAM_BOT_TOKEN=your-bot-token
```

### 4. Развертывание

**Вариант A: С переменными окружения (проще)**

```bash
docker stack deploy -c docker-compose.swarm.yml telegram-miniapp
```

**Вариант B: С Docker Secrets (безопаснее)**

```bash
# Создание secrets
echo "rootpassword" | docker secret create mysql_root_password -
echo "appuser" | docker secret create mysql_user -
echo "apppassword" | docker secret create mysql_password -
echo "your-secret-key" | docker secret create secret_key -
echo "your-bot-token" | docker secret create telegram_bot_token -

# Развертывание
docker stack deploy -c docker-stack.yml telegram-miniapp
```

### 5. Проверка

```bash
# Статус сервисов
docker stack services telegram-miniapp

# Логи
docker service logs -f telegram-miniapp_web
```

Приложение будет доступно на порту 5000 всех узлов кластера.

## Полезные команды

```bash
# Масштабирование
docker service scale telegram-miniapp_web=3

# Обновление
docker service update --image telegram_miniapp:latest telegram-miniapp_web

# Удаление
docker stack rm telegram-miniapp
```

Подробная документация: [DOCKER_SWARM.md](DOCKER_SWARM.md)

