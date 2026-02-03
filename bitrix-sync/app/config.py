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
    # Папка, где всегда лежат файлы для экспорта (по умолчанию .../bitrix-sync/app/uploads).
    # Имя файла берётся из таблицы form_submissions, столбец file_path.
    _default_uploads = str(Path(__file__).resolve().parent / 'uploads')
    EXPORT_UPLOAD_FOLDER = os.getenv('EXPORT_UPLOAD_FOLDER', _default_uploads)
    # ID папки на диске Bitrix24 для загрузки файлов (disk.folder.uploadfile)
    EXPORT_DISK_FOLDER_ID = os.getenv('EXPORT_DISK_FOLDER_ID', '200951')

    # Уровень логирования
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
