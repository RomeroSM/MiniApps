from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from config import Config
from database import db, init_db
from models import User
from telegram_validation import validate_telegram_webapp_data
from routes import api
import os

app = Flask(__name__)
app.config.from_object(Config)

# Настройка APPLICATION_ROOT для работы за префиксом (например, /form)
# Приоритет: переменная окружения APPLICATION_ROOT > автоматическое определение
if Config.APPLICATION_ROOT:
    app.config['APPLICATION_ROOT'] = Config.APPLICATION_ROOT

# Инициализация CORS
CORS(app)

# Регистрация Blueprint
app.register_blueprint(api, url_prefix='/api')

# Инициализация базы данных
init_db(app)


class ReverseProxied:
    """WSGI middleware для правильной работы за reverse proxy с префиксом"""
    def __init__(self, app, script_name=None):
        self.app = app
        self.script_name = script_name

    def __call__(self, environ, start_response):
        # Если SCRIPT_NAME не установлен, пытаемся определить из заголовков
        if not environ.get('SCRIPT_NAME'):
            # Проверяем заголовок X-Script-Name (может быть установлен Nginx)
            script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
            if script_name:
                environ['SCRIPT_NAME'] = script_name
            # Или используем значение из конфигурации
            elif self.script_name:
                environ['SCRIPT_NAME'] = self.script_name
        
        return self.app(environ, start_response)


# Применяем middleware для поддержки префикса
if Config.APPLICATION_ROOT:
    app.wsgi_app = ReverseProxied(app.wsgi_app, script_name=Config.APPLICATION_ROOT)
else:
    app.wsgi_app = ReverseProxied(app.wsgi_app)


def is_authorized_telegram_user(telegram_user_id):
    """Проверяет, есть ли пользователь с данным tg_id в базе данных"""
    if not telegram_user_id:
        return False

    user = User.query.filter_by(tg_id=telegram_user_id).first()
    return user is not None


@app.route('/')
def index():
    """Главная страница с формой"""
    # Проверяем, является ли запрос от Telegram WebApp
    init_data = request.args.get('tgWebAppData') or request.headers.get('X-Telegram-Init-Data')

    if init_data and Config.TELEGRAM_BOT_TOKEN:
        # Валидируем данные Telegram
        if not validate_telegram_webapp_data(init_data, Config.TELEGRAM_BOT_TOKEN):
            return render_template('index.html', error="Invalid Telegram WebApp data")

        # Извлекаем user_id из данных
        try:
            from urllib.parse import parse_qs, unquote
            parsed_data = parse_qs(unquote(init_data))
            if 'user' in parsed_data:
                import json
                user_data = json.loads(parsed_data['user'][0])
                telegram_user_id = user_data.get('id')

                # Проверяем, есть ли пользователь в базе данных
                if telegram_user_id and not is_authorized_telegram_user(telegram_user_id):
                    return render_template('index.html', error="Access denied: User is not registered in the system")
        except Exception as e:
            # Если не удается извлечь данные, продолжаем без проверки
            pass

    return render_template('index.html')


if __name__ == '__main__':
    import os
    debug_mode = os.getenv('FLASK_ENV') == 'development' or os.getenv('DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)


