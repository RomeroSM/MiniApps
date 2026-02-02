"""
Адаптер для работы моделей без Flask-SQLAlchemy
Создает объект db совместимый с Flask-SQLAlchemy, но использующий обычную SQLAlchemy
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
import sys
from pathlib import Path

# Добавляем путь к bitrix-sync для импорта Config
# Когда этот файл копируется как database.py в /app/, нужно добавить /app/bitrix-sync в путь
app_bitrix_sync = Path('/app/bitrix-sync')
if app_bitrix_sync.exists() and str(app_bitrix_sync) not in sys.path:
    sys.path.insert(0, str(app_bitrix_sync))

# Также добавляем текущую директорию (на случай если запускается из другого места)
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Пробуем импортировать Config из bitrix-sync
try:
    from app.config import Config
except ImportError:
    # Если не получается, пробуем из текущей директории
    import os
    bitrix_sync_path = os.path.join(os.path.dirname(__file__), 'bitrix-sync')
    if os.path.exists(bitrix_sync_path) and bitrix_sync_path not in sys.path:
        sys.path.insert(0, bitrix_sync_path)
    from app.config import Config

# Создаем базовый класс для моделей
Base = declarative_base()

# Создаем engine
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)

# Создаем session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


class SQLAlchemyAdapter:
    """Адаптер, имитирующий Flask-SQLAlchemy для работы с моделями"""
    
    def __init__(self):
        self.engine = engine
        self.session = Session
        # Model должен быть атрибутом, а не property, чтобы его можно было использовать в моделях
        self.Model = Base


# Создаем объект db совместимый с Flask-SQLAlchemy
db = SQLAlchemyAdapter()
