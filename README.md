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
6. **users** - пользователи системы (авторизация по Telegram ID)

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
API_TOKEN=your-api-token-for-authorization
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
API_TOKEN=your-api-token-for-authorization
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

**Важно:** Все API endpoints требуют авторизации через токен. Токен можно передать:
- Как query параметр: `?token=your-api-token`
- В теле запроса (JSON): `{"token": "your-api-token", ...}`
- В форме (form-data): `token=your-api-token`

Токен настраивается через переменную окружения `API_TOKEN`. Если токен не установлен, авторизация не требуется (для обратной совместимости).

### Справочники

#### Города

**GET /api/cities**
- Получить список всех городов
- Возвращает: массив объектов с полями `id`, `name`, `btxid`

**POST /api/cities**
- Создать новый город
- Параметры: `name` (обязательно), `btxid` (опционально)
- Возвращает: созданный объект города

**PUT /api/cities/<city_id>**
- Обновить город
- Параметры: `name` (опционально), `btxid` (опционально)
- Возвращает: обновленный объект города

#### Объекты

**GET /api/objects?city_id=X**
- Получить список объектов по городу
- Параметры: `city_id` (обязательно)
- Возвращает: массив объектов с полями `id`, `city_id`, `name`, `btxid`

**POST /api/objects**
- Создать новый объект
- Параметры: `city_id` (обязательно), `name` (обязательно), `btxid` (опционально)
- Возвращает: созданный объект

**PUT /api/objects/<object_id>**
- Обновить объект
- Параметры: `city_id` (опционально), `name` (опционально), `btxid` (опционально)
- Возвращает: обновленный объект

#### Категории нарушений

**GET /api/violation-categories**
- Получить список категорий нарушений
- Возвращает: массив объектов с полями `id`, `name`, `btxid`

**POST /api/violation-categories**
- Создать новую категорию нарушений
- Параметры: `name` (обязательно), `btxid` (опционально)
- Возвращает: созданную категорию

**PUT /api/violation-categories/<category_id>**
- Обновить категорию нарушений
- Параметры: `name` (опционально), `btxid` (опционально)
- Возвращает: обновленную категорию

#### Нарушения

**GET /api/violations?category_id=X**
- Получить список нарушений по категории
- Параметры: `category_id` (обязательно)
- Возвращает: массив объектов с полями `id`, `category_id`, `name`, `btxid`

**POST /api/violations**
- Создать новое нарушение
- Параметры: `category_id` (обязательно), `name` (обязательно), `btxid` (опционально)
- Возвращает: созданное нарушение

**PUT /api/violations/<violation_id>**
- Обновить нарушение
- Параметры: `category_id` (опционально), `name` (опционально), `btxid` (опционально)
- Возвращает: обновленное нарушение

#### Пользователи

**GET /api/users**
- Получить список всех пользователей (без секретных ключей)
- Возвращает: массив объектов с полями `id`, `first_name`, `last_name`, `tg_id`, `btxid`, `created_at`

**POST /api/users**
- Создать нового пользователя
- Параметры: `first_name`, `last_name`, `tg_id` (обязательно), `btxid` (опционально)
- Возвращает: данные пользователя с автоматически сгенерированным `secret_key`

**PUT /api/users/<user_id>**
- Обновить пользователя
- Параметры: `first_name` (опционально), `last_name` (опционально), `tg_id` (опционально), `btxid` (опционально)
- Возвращает: обновленный объект пользователя

**POST /api/users/check-access**
- Проверить доступ пользователя
- Параметры: `tg_id` (опционально, если не указан, извлекается из `X-Telegram-Init-Data`)
- Заголовок: `X-Telegram-Init-Data` (опционально, для извлечения tg_id)
- Возвращает: статус авторизации и данные пользователя (если найден)

### Формы

**POST /api/submit**
- Отправить форму
- Параметры: `city_id`, `object_id`, `violation_category_id`, `violation_id`, `comment` (опционально), `file` (опционально)
- Заголовок: `X-Telegram-Init-Data` (для валидации Telegram WebApp)
- **Требуется авторизация**: пользователь должен быть зарегистрирован в системе (проверка по Telegram ID)

**GET /api/submissions**
- Получить список отправленных форм (для администрирования)
- Параметры: `limit` (по умолчанию 50), `offset` (по умолчанию 0)

**GET /api/uploads/<filename>**
- Скачать загруженный файл

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
- 3 тестовых пользователя (для тестирования авторизации)

## Безопасность

- Валидация данных на сервере
- Проверка Telegram WebApp initData
- **Авторизация по Telegram ID**: только зарегистрированные пользователи могут отправлять формы
- Защита от SQL-инъекций через ORM
- Ограничение размера файлов (10 МБ)
- Проверка типов файлов

## Разрешенные типы файлов

- Изображения: PNG, JPG, JPEG, GIF
- Документы: PDF, DOC, DOCX, TXT

## Миграции базы данных

При обновлении базы данных колонки `btxid` будут автоматически добавлены при первом запуске приложения. Если нужно выполнить миграцию вручную, используйте SQL-скрипт из файла `migrations/add_btxid_columns.sql`.

### Выполнение миграции вручную

```bash
# В Docker
docker-compose exec db mysql -u appuser -p telegram_miniapp < migrations/add_btxid_columns.sql

# Локально
mysql -u root -p telegram_miniapp < migrations/add_btxid_columns.sql
```

## Примечания

- Для работы в Telegram необходимо развернуть приложение на HTTPS сервере
- Для локального тестирования можно использовать ngrok или аналогичные сервисы
- Валидация Telegram WebApp данных опциональна (можно отключить, убрав токен из .env)
- При первом запуске приложения автоматически проверяются и добавляются недостающие колонки `btxid` во все таблицы


