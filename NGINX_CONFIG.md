# Настройка Nginx для работы приложения за префиксом /form

## Проблема

Когда приложение доступно по адресу `https://site.name/form`, Flask не знает о префиксе `/form` и генерирует неправильные пути для статических файлов (например, `/static/css/style.css` вместо `/form/static/css/style.css`).

## Решение

Есть два способа решить эту проблему:

### Способ 1: Установить переменную окружения APPLICATION_ROOT (Рекомендуется)

В вашем `docker-compose.yml` или при запуске контейнера добавьте переменную окружения:

```yaml
environment:
  APPLICATION_ROOT: /form
```

Или при запуске контейнера:
```bash
docker run -e APPLICATION_ROOT=/form ...
```

### Способ 2: Настроить Nginx для передачи префикса

В конфигурации Nginx нужно передать префикс через заголовок `X-Script-Name` или через WSGI переменную `SCRIPT_NAME`.

#### Вариант 2.1: Использование заголовка X-Script-Name

```nginx
location /form {
    # Передаем префикс через заголовок
    proxy_set_header X-Script-Name /form;
    
    # Убираем префикс при проксировании к приложению
    rewrite ^/form(.*)$ $1 break;
    
    proxy_pass http://localhost:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Отдельный location для статических файлов
location /form/static {
    # Проксируем статические файлы с сохранением префикса
    proxy_pass http://localhost:5000/static;
    proxy_set_header Host $host;
}
```

#### Вариант 2.2: Использование uwsgi_param (если используется uWSGI)

```nginx
location /form {
    include uwsgi_params;
    uwsgi_param SCRIPT_NAME /form;
    uwsgi_modifier1 30;
    uwsgi_pass unix:///path/to/socket;
}
```

#### Вариант 2.3: Полная конфигурация для работы за префиксом

```nginx
server {
    listen 443 ssl http2;
    server_name site.name;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Главная страница формы
    location /form {
        # Передаем префикс через заголовок
        proxy_set_header X-Script-Name /form;
        
        # Убираем префикс при проксировании
        rewrite ^/form(.*)$ $1 break;
        
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Статические файлы (CSS, JS)
    location /form/static {
        proxy_pass http://localhost:5000/static;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Кеширование статических файлов
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API endpoints
    location /form/api {
        proxy_set_header X-Script-Name /form;
        rewrite ^/form(.*)$ $1 break;
        
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Проверка

После настройки проверьте:

1. Откройте `https://site.name/form` в браузере
2. Откройте инструменты разработчика (F12) → вкладка Network
3. Убедитесь, что запросы к CSS и JS файлам идут по правильным путям:
   - ✅ `https://site.name/form/static/css/style.css`
   - ✅ `https://site.name/form/static/js/app.js`
   - ❌ НЕ `https://site.name/static/css/style.css`

## Альтернативное решение (если ничего не помогает)

Если настройка Nginx сложна, можно использовать переменную окружения `APPLICATION_ROOT=/form` при запуске контейнера - это самый простой способ.
