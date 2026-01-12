# Публикация образа в Docker Hub

## Быстрый способ (рекомендуется)

Запустите интерактивный скрипт:

```powershell
.\push-to-dockerhub-simple.ps1
```

Скрипт запросит:
1. Ваше имя пользователя Docker Hub
2. Учетные данные для входа (пароль или токен доступа)

## Ручная публикация

Если хотите выполнить команды вручную:

### 1. Тегирование образа

Замените `YOUR_USERNAME` на ваше имя пользователя Docker Hub:

```powershell
docker tag telegram_miniapp:latest YOUR_USERNAME/telegram_miniapp:latest
```

### 2. Вход в Docker Hub

```powershell
docker login
```

Введите:
- Username: ваше имя пользователя Docker Hub
- Password: ваш пароль или токен доступа

> **Примечание:** Если у вас включена двухфакторная аутентификация, нужно использовать токен доступа вместо пароля.
> Создать токен: https://hub.docker.com/settings/security → New Access Token

### 3. Публикация образа

```powershell
docker push YOUR_USERNAME/telegram_miniapp:latest
```

Это может занять несколько минут в зависимости от скорости интернета.

### 4. Проверка

После успешной публикации образ будет доступен по адресу:

```
https://hub.docker.com/r/YOUR_USERNAME/telegram_miniapp
```

Для скачивания образа используйте:

```powershell
docker pull YOUR_USERNAME/telegram_miniapp:latest
```

## Публикация с конкретной версией

Рекомендуется также публиковать образы с тегами версий:

```powershell
# Тегирование с версией
docker tag telegram_miniapp:latest YOUR_USERNAME/telegram_miniapp:v1.0.0

# Публикация версии
docker push YOUR_USERNAME/telegram_miniapp:v1.0.0
```

## Использование образа из Docker Hub в Docker Swarm

После публикации обновите `docker-compose.swarm.yml`:

```yaml
web:
  image: YOUR_USERNAME/telegram_miniapp:latest
  # ... остальная конфигурация
```

Затем разверните:

```powershell
docker stack deploy -c docker-compose.swarm.yml telegram-miniapp
```

