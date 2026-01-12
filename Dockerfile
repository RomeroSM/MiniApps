FROM python:3.11-slim

WORKDIR /app

# PyMySQL - чистый Python драйвер, не требует нативных библиотек MySQL
# Поэтому не нужно устанавливать default-libmysqlclient-dev

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей с retry логикой
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY . .

# Создание папки для загрузок
RUN mkdir -p uploads && chmod 755 uploads

# Открытие порта
EXPOSE 5000

# Переменные окружения по умолчанию
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Запуск приложения
CMD ["python", "app.py"]

