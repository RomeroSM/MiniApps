# Инструкция по развертыванию в Docker Swarm

## Подготовка

### 1. Инициализация Swarm кластера

На главном узле (manager) выполните:

```bash
docker swarm init
```

Если у вас несколько сетевых интерфейсов, укажите адрес:

```bash
docker swarm init --advertise-addr <IP-адрес>
```

Вы увидите команду для присоединения worker узлов. Сохраните её.

### 2. Присоединение worker узлов (опционально)

На каждом worker узле выполните команду, полученную на шаге 1:

```bash
docker swarm join --token <token> <manager-ip>:2377
```

### 3. Проверка статуса кластера

```bash
docker node ls
```

## Вариант 1: Развертывание с переменными окружения (проще)

### Шаг 1: Сборка образа

На manager узле соберите образ:

```bash
docker build -t telegram_miniapp:latest .
```

Если у вас несколько узлов, загрузите образ в registry илиам9с   экспортируйте:

```bash
# Сохранение образа
docker save telegram_miniapp:latest | gzip > telegram_miniapp.tar.gz

# На других узлах - загрузка
docker load < telegram_miniapp.tar.gz
```

Или используйте Docker Registry:

```bash
# Тегирование для registry
docker tag telegram_miniapp:latest your-registry.com/telegram_miniapp:latest

# Отправка в registry
docker push your-registry.com/telegram_miniapp:latest
```

### Шаг 2: Создание .env файла

Создайте файл `.env` с переменными окружения:

```env
MYSQL_ROOT_PASSWORD=secure-root-password
MYSQL_USER=appuser
MYSQL_PASSWORD=secure-app-password
MYSQL_DATABASE=telegram_miniapp
SECRET_KEY=your-secret-key-here
TELEGRAM_BOT_TOKEN=your-bot-token-here
```

### Шаг 3: Развертывание stack

```bash
docker stack deploy -c docker-compose.swarm.yml telegram-miniapp
```

### Шаг 4: Проверка статуса

```bash
# Список сервисов
docker service ls

# Детали сервиса
docker service ps telegram-miniapp_web
docker service ps telegram-miniapp_db

# Логи
docker service logs telegram-miniapp_web
docker service logs telegram-miniapp_db
```

## Вариант 2: Развертывание с Docker Secrets (рекомендуется для production)

### Шаг 1: Создание secrets

```bash
# MySQL root пароль
echo "secure-root-password" | docker secret create mysql_root_password -

# MySQL пользователь
echo "appuser" | docker secret create mysql_user -

# MySQL пароль
echo "secure-app-password" | docker secret create mysql_password -

# Flask secret key
echo "your-secret-key-here" | docker secret create secret_key -

# Telegram bot token
echo "your-bot-token-here" | docker secret create telegram_bot_token -
```

### Шаг 2: Проверка secrets

```bash
docker secret ls
```

### Шаг 3: Обновление кода для работы с secrets

Нужно обновить `config.py` и `app.py` для чтения secrets из файлов:

**config.py:**
```python
import os
from pathlib import Path

def read_secret(secret_name, default=None):
    """Читает secret из файла или переменной окружения"""
    secret_file = Path(f'/run/secrets/{secret_name}')
    if secret_file.exists():
        return secret_file.read_text().strip()
    return os.getenv(secret_name, default)

class Config:
    SECRET_KEY = read_secret('secret_key', os.getenv('SECRET_KEY', 'dev-secret-key'))
    
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'db')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = read_secret('mysql_user', os.getenv('MYSQL_USER', 'root'))
    MYSQL_PASSWORD = read_secret('mysql_password', os.getenv('MYSQL_PASSWORD', ''))
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'telegram_miniapp')
    
    TELEGRAM_BOT_TOKEN = read_secret('telegram_bot_token', os.getenv('TELEGRAM_BOT_TOKEN', ''))
    
    # ... остальные настройки
```

### Шаг 4: Развертывание stack

```bash
docker stack deploy -c docker-stack.yml telegram-miniapp
```

## Управление Stack

### Просмотр статуса

```bash
# Список всех сервисов в stack
docker stack services telegram-miniapp

# Детали сервиса
docker service inspect telegram-miniapp_web --pretty

# Логи сервиса
docker service logs -f telegram-miniapp_web

# Масштабирование сервиса
docker service scale telegram-miniapp_web=3
```

### Обновление приложения

```bash
# 1. Соберите новый образ
docker build -t telegram_miniapp:latest .

# 2. Обновите сервис
docker service update --image telegram_miniapp:latest telegram-miniapp_web

# Или обновите весь stack
docker stack deploy -c docker-compose.swarm.yml telegram-miniapp
```

### Откат обновления

```bash
docker service rollback telegram-miniapp_web
```

### Удаление stack

```bash
docker stack rm telegram-miniapp
```

## Масштабирование

### Увеличение количества реплик

```bash
# Увеличить до 3 реплик веб-сервиса
docker service scale telegram-miniapp_web=3
```

Или измените в `docker-compose.swarm.yml`:

```yaml
deploy:
  replicas: 3
```

Затем обновите stack:

```bash
docker stack deploy -c docker-compose.swarm.yml telegram-miniapp
```

## Мониторинг

### Просмотр ресурсов

```bash
# Использование ресурсов узлами
docker stats

# Детали узла
docker node inspect <node-id> --pretty
```

### Логи

```bash
# Все логи сервиса
docker service logs telegram-miniapp_web

# Последние 100 строк
docker service logs --tail 100 telegram-miniapp_web

# Логи в реальном времени
docker service logs -f telegram-miniapp_web
```

## Troubleshooting

### Проблема: Сервис не запускается

```bash
# Проверьте статус
docker service ps telegram-miniapp_web --no-trunc

# Проверьте логи
docker service logs telegram-miniapp_web

# Проверьте конфигурацию
docker service inspect telegram-miniapp_web --pretty
```

### Проблема: База данных не доступна

```bash
# Проверьте, что БД запущена на manager узле
docker service ps telegram-miniapp_db

# Проверьте сеть
docker network ls
docker network inspect telegram-miniapp_app-network
```

### Проблема: Образ не найден на worker узлах

```bash
# На manager узле экспортируйте образ
docker save telegram_miniapp:latest > telegram_miniapp.tar

# На worker узле загрузите образ
docker load < telegram_miniapp.tar
```

Или используйте Docker Registry.

### Проблема: Secrets не работают

Убедитесь, что:
1. Secrets созданы: `docker secret ls`
2. В docker-stack.yml указаны правильные имена secrets
3. Код обновлен для чтения из `/run/secrets/`

## Production рекомендации

1. **Используйте Docker Secrets** для чувствительных данных
2. **Настройте reverse proxy** (Traefik, Nginx) для HTTPS
3. **Используйте внешнюю БД** или managed MySQL сервис
4. **Настройте мониторинг** (Prometheus, Grafana)
5. **Настройте логирование** (ELK stack, Loki)
6. **Используйте healthchecks** для автоматического перезапуска
7. **Настройте backup** для базы данных
8. **Используйте placement constraints** для распределения нагрузки

## Пример с Traefik (опционально)

Если используете Traefik как reverse proxy, в `docker-stack.yml` уже есть labels для Traefik. Добавьте сервис Traefik в stack:

```yaml
traefik:
  image: traefik:v2.10
  command:
    - "--api.insecure=true"
    - "--providers.docker.swarmmode=true"
    - "--providers.docker.exposedbydefault=false"
    - "--entrypoints.web.address=:80"
    - "--entrypoints.websecure.address=:443"
    - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
    - "--certificatesresolvers.letsencrypt.acme.email=your@email.com"
    - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
  ports:
    - "80:80"
    - "443:443"
    - "8080:8080"
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - traefik_letsencrypt:/letsencrypt
  networks:
    - app-network
  deploy:
    placement:
      constraints:
        - node.role == manager
```

## Полезные команды

```bash
# Список всех узлов
docker node ls

# Информация об узле
docker node inspect <node-id>

# Промоутинг worker в manager
docker node promote <node-id>

# Демоутинг manager в worker
docker node demote <node-id>

# Удаление узла
docker node rm <node-id>

# Список всех stacks
docker stack ls

# Список всех сервисов
docker service ls

# Список всех secrets
docker secret ls

# Список всех volumes
docker volume ls
```

