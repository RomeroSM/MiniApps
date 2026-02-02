FROM python:3.11-slim

WORKDIR /app

# Копирование файлов зависимостей
COPY bitrix-sync/requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование моделей из родительского проекта (нужны для синхронизации)
# Модели должны быть в /app/, так как database.py ищет их в родительской директории
COPY models.py ./

# Копирование адаптера database для работы без Flask
# Этот файл будет использоваться как database.py для импорта в models.py
COPY bitrix-sync/database_adapter.py ./database.py

# Копирование приложения bitrix-sync
COPY bitrix-sync/ ./bitrix-sync/

# Создание рабочей директории для bitrix-sync
WORKDIR /app/bitrix-sync

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1

# Запуск сервиса синхронизации
CMD ["python", "service.py"]
