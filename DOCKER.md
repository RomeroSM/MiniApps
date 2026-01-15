# Инструкция по запуску в Docker

## Быстрый старт

1. **Создайте файл `.env`** (скопируйте из примера ниже):

```env
SECRET_KEY=your-secret-key-change-this
MYSQL_ROOT_PASSWORD=secure-root-password
MYSQL_USER=appuser
MYSQL_PASSWORD=secure-app-password
MYSQL_DATABASE=telegram_miniapp
TELEGRAM_BOT_TOKEN=your-bot-token-here
API_TOKEN=your-api-token-for-authorization
```

2. **Запустите приложение**:

```bash
docker-compose up -d
```

3. **Проверьте логи**:

```bash
docker-compose logs -f web
```

Приложение будет доступно по адресу: `http://localhost:5000`

## Полезные команды

### Управление контейнерами

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Остановка с удалением данных БД
docker-compose down -v

# Перезапуск
docker-compose restart

# Пересборка после изменений кода
docker-compose build --no-cache
docker-compose up -d
```

### Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Только веб-приложение
docker-compose logs -f web

# Только база данных
docker-compose logs -f db
```

### Работа с базой данных

```bash
# Подключение к MySQL
docker-compose exec db mysql -u appuser -p telegram_miniapp

# Резервное копирование БД
docker-compose exec db mysqldump -u appuser -p telegram_miniapp > backup.sql

# Восстановление БД
docker-compose exec -T db mysql -u appuser -p telegram_miniapp < backup.sql
```

### Выполнение команд в контейнере

```bash
# Python shell
docker-compose exec web python

# Bash shell
docker-compose exec web bash

# Проверка статуса
docker-compose ps
```

## Структура

- **web** - Flask приложение (порт 5000)
- **db** - MySQL база данных (порт 3306)
- **uploads/** - загруженные файлы (монтируется как volume)

## Переменные окружения

Все переменные окружения можно задать в файле `.env` или передать через `docker-compose.yml`.

### Важные переменные:

- `SECRET_KEY` - секретный ключ Flask (обязательно измените в production)
- `MYSQL_ROOT_PASSWORD` - пароль root пользователя MySQL
- `MYSQL_USER` - пользователь приложения
- `MYSQL_PASSWORD` - пароль пользователя приложения
- `MYSQL_DATABASE` - имя базы данных
- `TELEGRAM_BOT_TOKEN` - токен Telegram бота (опционально)
- `API_TOKEN` - токен для авторизации API запросов (опционально, если не установлен, авторизация не требуется)

## Troubleshooting

### Проблема: Контейнер web не запускается

**Решение**: Проверьте логи:
```bash
docker-compose logs web
```

Возможные причины:
- База данных еще не готова (подождите несколько секунд)
- Неверные учетные данные БД
- Порт 5000 уже занят

### Проблема: Ошибка подключения к БД

**Решение**: 
1. Убедитесь, что контейнер `db` запущен: `docker-compose ps`
2. Проверьте переменные окружения в `.env`
3. Проверьте логи БД: `docker-compose logs db`

### Проблема: Файлы не сохраняются

**Решение**: Убедитесь, что папка `uploads` существует и имеет правильные права:
```bash
mkdir -p uploads
chmod 755 uploads
```

### Очистка и пересоздание

Если нужно полностью пересоздать окружение:

```bash
# Остановка и удаление контейнеров, volumes и сетей
docker-compose down -v

# Удаление образов
docker-compose rm -f

# Пересборка и запуск
docker-compose build --no-cache
docker-compose up -d
```

## Production deployment

Для production рекомендуется:

1. Использовать внешнюю БД или managed MySQL сервис
2. Настроить reverse proxy (nginx) с SSL
3. Использовать переменные окружения для чувствительных данных
4. Настроить мониторинг и логирование
5. Использовать production WSGI сервер (gunicorn) вместо встроенного Flask сервера

Пример с gunicorn:

```dockerfile
# В Dockerfile заменить CMD на:
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
```

И добавить в `requirements.txt`:
```
gunicorn==21.2.0
```

