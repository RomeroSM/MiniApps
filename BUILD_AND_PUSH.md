# Инструкция по сборке и публикации Docker образа в приватный реестр

## Быстрый старт

### Вариант 1: Использование скрипта (рекомендуется)

#### Для Windows (PowerShell):
```powershell
.\build-and-push.ps1 your-registry.com telegram_miniapp latest
```

#### Для Linux/Mac:
```bash
chmod +x build-and-push.sh
./build-and-push.sh your-registry.com telegram_miniapp latest
```

### Вариант 2: Ручная сборка и публикация

#### 1. Сборка образа
```bash
docker build -t telegram_miniapp:latest .
```

#### 2. Тегирование для реестра
```bash
docker tag telegram_miniapp:latest your-registry.com/telegram_miniapp:latest
```

#### 3. Вход в реестр (если требуется аутентификация)
```bash
docker login your-registry.com
```

#### 4. Публикация образа
```bash
docker push your-registry.com/telegram_miniapp:latest
```

## Примеры для различных реестров

### Docker Hub (публичный) - РЕКОМЕНДУЕТСЯ

**Самый простой способ - используйте скрипт:**
```powershell
# Windows PowerShell - интерактивный скрипт
.\push-to-dockerhub-simple.ps1
```

**Или вручную:**
```bash
# 1. Тегирование образа (замените YOUR_USERNAME на ваше имя пользователя)
docker tag telegram_miniapp:latest YOUR_USERNAME/telegram_miniapp:latest

# 2. Вход в Docker Hub (потребуются учетные данные)
docker login

# 3. Публикация
docker push YOUR_USERNAME/telegram_miniapp:latest
```

**После публикации образ будет доступен по адресу:**
```
https://hub.docker.com/r/YOUR_USERNAME/telegram_miniapp
```

### GitHub Container Registry (ghcr.io)
```bash
docker tag telegram_miniapp:latest ghcr.io/your-username/telegram_miniapp:latest
docker login ghcr.io -u your-username
docker push ghcr.io/your-username/telegram_miniapp:latest
```

### GitLab Container Registry
```bash
docker tag telegram_miniapp:latest registry.gitlab.com/your-username/your-project/telegram_miniapp:latest
docker login registry.gitlab.com
docker push registry.gitlab.com/your-username/your-project/telegram_miniapp:latest
```

### Приватный реестр (обычный)
```bash
docker tag telegram_miniapp:latest registry.example.com:5000/telegram_miniapp:latest
docker login registry.example.com:5000
docker push registry.example.com:5000/telegram_miniapp:latest
```

### Harbor
```bash
docker tag telegram_miniapp:latest harbor.example.com/your-project/telegram_miniapp:latest
docker login harbor.example.com
docker push harbor.example.com/your-project/telegram_miniapp:latest
```

## Использование образа из реестра в Docker Swarm

После публикации образа в реестр, обновите `docker-compose.swarm.yml`:

```yaml
web:
  image: your-registry.com/telegram_miniapp:latest
  # ... остальная конфигурация
```

Затем разверните stack:
```bash
docker stack deploy -c docker-compose.swarm.yml telegram-miniapp
```

## Проверка публикации

Убедитесь, что образ доступен в реестре:
```bash
# Для Docker Hub
docker pull your-username/telegram_miniapp:latest

# Для приватного реестра
docker pull your-registry.com/telegram_miniapp:latest
```

## Переменные окружения для скрипта

Вы можете использовать переменные окружения:

```bash
export DOCKER_REGISTRY="your-registry.com"
export IMAGE_NAME="telegram_miniapp"
export IMAGE_TAG="latest"
```

Или создать файл `.env.registry`:
```
DOCKER_REGISTRY=your-registry.com
IMAGE_NAME=telegram_miniapp
IMAGE_TAG=latest
```

## Советы

1. **Используйте теги версий** вместо `latest` для production:
   ```bash
   docker tag telegram_miniapp:latest your-registry.com/telegram_miniapp:v1.0.0
   ```

2. **Многоархитектурные образы**: Для поддержки разных архитектур используйте `docker buildx`:
   ```bash
   docker buildx build --platform linux/amd64,linux/arm64 -t your-registry.com/telegram_miniapp:latest --push .
   ```

3. **Автоматизация через CI/CD**: Добавьте эти команды в ваш CI/CD pipeline

4. **Безопасность**: Не храните учетные данные в скриптах. Используйте Docker secrets или переменные окружения

