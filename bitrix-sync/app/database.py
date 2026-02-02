import sys
import os
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session

logger = logging.getLogger(__name__)

# Добавляем родительскую директорию в путь для импорта models
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Импортируем Config до импорта models
from app.config import Config

# Создаем engine для работы с БД
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)

# Создаем session factory
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))

# Кэш для моделей
_models_cache = None


def get_session():
    """Получить сессию базы данных"""
    return SessionLocal()


def ensure_objects_state_column():
    """Добавить колонку state в таблицу objects, если её нет (для работы синка до перезапуска web)."""
    try:
        with engine.connect() as conn:
            r = conn.execute(text(
                "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'objects' AND COLUMN_NAME = 'state'"
            ))
            if r.fetchone()[0] > 0:
                return
            conn.execute(text(
                "ALTER TABLE objects ADD COLUMN state VARCHAR(100) NULL DEFAULT NULL AFTER btxid"
            ))
            conn.commit()
            logger.info("Added state column to objects table")
    except Exception as e:
        if "Duplicate column name" not in str(e):
            logger.warning("Could not add state column to objects: %s", e)


def ensure_violations_state_column():
    """Добавить колонку state в таблицу violations, если её нет (для работы синка до перезапуска web)."""
    try:
        with engine.connect() as conn:
            r = conn.execute(text(
                "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'violations' AND COLUMN_NAME = 'state'"
            ))
            if r.fetchone()[0] > 0:
                return
            conn.execute(text(
                "ALTER TABLE violations ADD COLUMN state VARCHAR(100) NULL DEFAULT NULL AFTER btxid"
            ))
            conn.commit()
            logger.info("Added state column to violations table")
    except Exception as e:
        if "Duplicate column name" not in str(e):
            logger.warning("Could not add state column to violations: %s", e)


def get_models():
    """Получить модели из родительского проекта"""
    global _models_cache
    
    if _models_cache is not None:
        return _models_cache
    
    # Импортируем модели
    # Модели из родительского проекта используют Flask-SQLAlchemy, но мы можем
    # работать с ними через обычную SQLAlchemy session
    from models import City, Object, ViolationCategory, Violation, User, FormSubmission
    
    _models_cache = {
        'City': City,
        'Object': Object,
        'ViolationCategory': ViolationCategory,
        'Violation': Violation,
        'User': User,
        'FormSubmission': FormSubmission
    }
    
    return _models_cache
