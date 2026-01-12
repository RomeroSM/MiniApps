# Telegram Mini App - Форма ввода данных

Telegram Mini App на Flask с MySQL для ввода данных о нарушениях с каскадными выпадающими списками.

## Возможности

- Каскадные выпадающие списки (Город → Объект, Категория нарушения → Нарушение)
- Загрузка файлов (до 10 МБ)
- Валидация данных на клиенте и сервере
- Интеграция с Telegram WebApp API
- Адаптивный дизайн в стиле Telegram

## Структура базы данных

### Таблицы:

1. **cities** - города
2. **objects** - объекты (связаны с городами)
3. **violation_categories** - категории нарушений
4. **violations** - нарушения (связаны с категориями)
5. **form_submissions** - отправленные формы

## Установка

### 1. Клонирование и установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка базы данных MySQL

Создайте базу данных:

```sql
CREATE DATABASE telegram_miniapp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Настройка переменных окружения

Создайте файл `.env` на основе `.env.example`:

```env
SECRET_KEY=your-secret-key-here
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=telegram_miniapp
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
```

### 4. Запуск приложения

```bash
python app.py
```

Приложение будет доступно по адресу: `http://localhost:5000`

## Публикация образа в приватный реестр

Для production окружения рекомендуется опубликовать образ в приватный Docker Registry. Подробная инструкция в файле [BUILD_AND_PUSH.md](BUILD_AND_PUSH.md).

**Быстрая команда:**
```bash
# Windows PowerShell
.\build-and-push.ps1 your-registry.com telegram_miniapp latest

# Linux/Mac
./build-and-push.sh your-registry.com telegram_miniapp latest
```

**Или вручную:**
```bash
docker build -t telegram_miniapp:latest .
docker tag telegram_miniapp:latest your-registry.com/telegram_miniapp:latest
docker login your-registry.com
docker push your-registry.com/telegram_miniapp:latest
```

## Установка через Docker Compose (development и production)

### 1. Настройка переменных окружения

Создайте файл `.env` на основе `.env.example`:

```env
SECRET_KEY=your-secret-key-here
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_USER=appuser
MYSQL_PASSWORD=apppassword
MYSQL_DATABASE=telegram_miniapp
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
```

### 2. Запуск с Docker Compose

```bash
# Сборка и запуск контейнеров
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка контейнеров
docker-compose down

# Остановка с удалением volumes (удалит данные БД)
docker-compose down -v
```

Приложение будет доступно по адресу: `http://localhost:5000`

### 3. Работа с Docker

```bash
# Пересборка образов после изменений
docker-compose build

# Перезапуск сервисов
docker-compose restart

# Просмотр статуса
docker-compose ps

# Выполнение команд в контейнере
docker-compose exec web python
docker-compose exec db mysql -u appuser -p telegram_miniapp
```

### 4. Структура Docker

- **Dockerfile** - образ Flask приложения
- **docker-compose.yml** - оркестрация сервисов (web + MySQL)
- **.dockerignore** - исключения при сборке образа

Docker Compose автоматически:
- Создает и настраивает MySQL базу данных
- Ожидает готовности БД перед запуском приложения
- Монтирует папку `uploads` для сохранения файлов
- Настраивает сеть между контейнерами

## Настройка Telegram Bot

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите токен бота
3. Настройте Web App:
   ```
   /newapp
   ```
   Укажите название и URL вашего приложения (например, `https://yourdomain.com`)
4. Добавьте токен в файл `.env`

## API Endpoints

### GET /api/cities
Получить список всех городов

### GET /api/objects?city_id=X
Получить список объектов по городу

### GET /api/violation-categories
Получить список категорий нарушений

### GET /api/violations?category_id=X
Получить список нарушений по категории

### POST /api/submit
Отправить форму
- Параметры: `city_id`, `object_id`, `violation_category_id`, `violation_id`, `comment` (опционально), `file` (опционально)
- Заголовок: `X-Telegram-Init-Data` (для валидации Telegram WebApp)

### GET /api/submissions
Получить список отправленных форм (для администрирования)

### GET /api/uploads/<filename>
Скачать загруженный файл

## Структура проекта

```
MiniApps/
├── app.py                 # Главный Flask файл
├── config.py              # Конфигурация
├── models.py              # SQLAlchemy модели
├── database.py            # Инициализация БД
├── routes.py              # API маршруты
├── telegram_validation.py # Валидация Telegram WebApp
├── requirements.txt       # Зависимости
├── static/
│   ├── css/
│   │   └── style.css      # Стили
│   └── js/
│       └── app.js         # JavaScript логика
├── templates/
│   └── index.html         # HTML форма
└── uploads/               # Загруженные файлы
```

## Тестирование

При первом запуске приложение автоматически создаст таблицы и добавит тестовые данные:
- 3 города (Москва, Санкт-Петербург, Новосибирск)
- Объекты для Москвы и Санкт-Петербурга
- 3 категории нарушений
- Нарушения для каждой категории

## Безопасность

- Валидация данных на сервере
- Проверка Telegram WebApp initData
- Защита от SQL-инъекций через ORM
- Ограничение размера файлов (10 МБ)
- Проверка типов файлов

## Разрешенные типы файлов

- Изображения: PNG, JPG, JPEG, GIF
- Документы: PDF, DOC, DOCX, TXT

## Примечания

- Для работы в Telegram необходимо развернуть приложение на HTTPS сервере
- Для локального тестирования можно использовать ngrok или аналогичные сервисы
- Валидация Telegram WebApp данных опциональна (можно отключить, убрав токен из .env)


