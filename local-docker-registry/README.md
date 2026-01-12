# Локальный Docker Registry

Этот репозиторий содержит настройки для запуска локального Docker Registry на вашей машине.

## Быстрый старт

### Запуск registry

```bash
docker-compose up -d
```

Registry будет доступен по адресу: `localhost:5000`

### Проверка работы

```bash
curl http://localhost:5000/v2/
```

Должен вернуться пустой ответ (статус 200).

## Использование

### Настройка Docker для работы с локальным registry (без TLS)

По умолчанию Docker не позволяет push в insecure registry. Для Windows нужно добавить настройку в Docker Desktop:

1. Откройте Docker Desktop
2. Перейдите в Settings → Docker Engine
3. Добавьте следующую конфигурацию:

```json
{
  "insecure-registries": ["localhost:5000"]
}
```

4. Нажмите "Apply & Restart"

### Тегирование и отправка образов

```bash
# Тегирование образа для локального registry
docker tag your-image:tag localhost:5000/your-image:tag

# Отправка образа в локальный registry
docker push localhost:5000/your-image:tag
```

### Получение образов из локального registry

```bash
docker pull localhost:5000/your-image:tag
```

### Просмотр списка образов в registry

```bash
# Список всех репозиториев
curl http://localhost:5000/v2/_catalog

# Список тегов конкретного репозитория
curl http://localhost:5000/v2/your-image/tags/list
```

## Примеры использования

### Пример 1: Тегирование и отправка существующего образа

```bash
# Тегируем образ
docker tag telegram-miniapp:latest localhost:5000/telegram-miniapp:latest

# Отправляем в локальный registry
docker push localhost:5000/telegram-miniapp:latest
```

### Пример 2: Использование в docker-compose

```yaml
services:
  app:
    image: localhost:5000/telegram-miniapp:latest
    # ... остальная конфигурация
```

### Пример 3: Использование в Docker Swarm

```yaml
services:
  web:
    image: localhost:5000/telegram-miniapp:latest
    # ... остальная конфигурация
```

**Важно**: Для Docker Swarm на всех узлах должен быть настроен `insecure-registries` в Docker Engine.

## Управление данными

### Просмотр размера volume

```bash
docker volume ls
docker volume inspect local-docker-registry_registry-data
```

### Остановка registry

```bash
docker-compose down
```

### Остановка с удалением данных

```bash
docker-compose down -v
```

## Настройка TLS (опционально)

Для использования TLS сертификатов:

1. Создайте папку `certs` в этой директории
2. Поместите туда `domain.crt` и `domain.key`
3. Раскомментируйте строки с volumes для certs в `docker-compose.yml`
4. Измените порт и используйте `https://` вместо `http://`

## Полезные команды

```bash
# Просмотр логов
docker-compose logs -f registry

# Перезапуск registry
docker-compose restart registry

# Проверка статуса
docker-compose ps
```

## Очистка старых образов

Локальный registry не удаляет старые образы автоматически. Для очистки можно использовать:

```bash
# Подключиться к контейнеру registry
docker exec -it local-docker-registry sh

# Использовать registry garbage collection (требует настройки)
# Или просто удалить volume и пересоздать
docker-compose down -v
docker-compose up -d
```

## Проблемы и решения

### Ошибка: "http: server gave HTTP response to HTTPS client"

Убедитесь, что вы настроили `insecure-registries` в Docker Desktop.

### Ошибка: "connection refused"

Проверьте, что registry запущен:
```bash
docker-compose ps
```

### Образы не видны на других узлах Swarm

Убедитесь, что на всех узлах Swarm настроен `insecure-registries` в `/etc/docker/daemon.json` (Linux) или в Docker Desktop (Windows).




