from flask import Flask, render_template, request
from flask_cors import CORS
from config import Config
from database import db, init_db
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


@app.route('/')
def index():
    """Главная страница с формой"""
    return render_template('index.html')


if __name__ == '__main__':
    import os
    debug_mode = os.getenv('FLASK_ENV') == 'development' or os.getenv('DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)


