import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из корневой директории проекта (родительская директория)
root_env_path = Path(__file__).parent.parent.parent / '.env'
if root_env_path.exists():
    load_dotenv(root_env_path)
else:
    # Если корневой .env не найден, пытаемся загрузить локальный
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
    """Конфигурация приложения синхронизации с Bitrix24"""
    
    # Bitrix24 Webhook URL
    BITRIX_WEBHOOK_URL = os.getenv('BITRIX_WEBHOOK_URL', '')
    
    # MySQL Database configuration
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = read_secret('mysql_user', os.getenv('MYSQL_USER', 'root'))
    MYSQL_PASSWORD = read_secret('mysql_password', os.getenv('MYSQL_PASSWORD', ''))
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'telegram_miniapp')
    
    # SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Расписание синхронизации (cron-формат, по умолчанию раз в сутки в полночь)
    SYNC_SCHEDULE = os.getenv('SYNC_SCHEDULE', '0 0 * * *')
    # Расписание экспорта заявок в Bitrix (раз в минуту)
    EXPORT_SCHEDULE = os.getenv('EXPORT_SCHEDULE', '* * * * *')

    # Экспорт form_submissions в список Bitrix (IBLOCK_ID=125)
    EXPORT_IBLOCK_TYPE_ID = os.getenv('EXPORT_IBLOCK_TYPE_ID', 'bitrix_processes')
    EXPORT_IBLOCK_ID = os.getenv('EXPORT_IBLOCK_ID', '125')
    # Коды свойств списка 125 (если пусто — в элемент передаётся только NAME)
    EXPORT_PROPERTY_CITY = os.getenv('EXPORT_PROPERTY_CITY', '')
    EXPORT_PROPERTY_OBJECT = os.getenv('EXPORT_PROPERTY_OBJECT', '')
    EXPORT_PROPERTY_CATEGORY = os.getenv('EXPORT_PROPERTY_CATEGORY', '')
    EXPORT_PROPERTY_VIOLATION = os.getenv('EXPORT_PROPERTY_VIOLATION', '')
    EXPORT_PROPERTY_COMMENT = os.getenv('EXPORT_PROPERTY_COMMENT', '')
    EXPORT_PROPERTY_FILE = os.getenv('EXPORT_PROPERTY_FILE', '')
    EXPORT_PROPERTY_TELEGRAM_USER_ID = os.getenv('EXPORT_PROPERTY_TELEGRAM_USER_ID', '')

    # Уровень логирования
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
