import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def read_secret(secret_name, default=None):
    """
    Читает secret из переменной окружения.
    """
    # Читаем из переменной окружения
    env_var = os.getenv(secret_name.upper())
    if env_var:
        return env_var

    # Пробуем вариант с _FILE суффиксом (Docker Compose style)
    file_path_env = os.getenv(f'{secret_name.upper()}_FILE')
    if file_path_env:
        try:
            return Path(file_path_env).read_text().strip()
        except Exception:
            pass

    return default


class Config:
    SECRET_KEY = read_secret('secret_key', os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'))
    
    # MySQL Database configuration
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = read_secret('mysql_user', os.getenv('MYSQL_USER', 'root'))
    MYSQL_PASSWORD = read_secret('mysql_password', os.getenv('MYSQL_PASSWORD', ''))
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'telegram_miniapp')
    
    # Telegram Bot Token (для проверки WebApp данных)
    TELEGRAM_BOT_TOKEN = read_secret('telegram_bot_token', os.getenv('TELEGRAM_BOT_TOKEN', ''))
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}
    
    # SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Префикс приложения (для работы за /form и т.п.)
    # Можно задать через переменную окружения APPLICATION_ROOT
    APPLICATION_ROOT = os.getenv('APPLICATION_ROOT')
    
    # Application root для работы за префиксом (например, /form)
    # Устанавливается через переменную окружения APPLICATION_ROOT или автоматически определяется
    APPLICATION_ROOT = os.getenv('APPLICATION_ROOT', None)


