import time
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from sqlalchemy import text

db = SQLAlchemy()


def init_db(app: Flask):
    """Инициализация базы данных"""
    db.init_app(app)
    
    with app.app_context():
        # Ожидание готовности БД (для Docker)
        max_retries = 30
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Проверка подключения к БД
                db.engine.connect()
                # Создание всех таблиц
                db.create_all()
                
                # Проверка и добавление недостающих колонок btxid
                _add_missing_btxid_columns()
                
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise Exception(f"Не удалось подключиться к базе данных после {max_retries} попыток: {e}")
                time.sleep(2)
        
        # Добавление тестовых данных, если таблицы пустые
        from models import City, Object, ViolationCategory, Violation, User
        
        if City.query.count() == 0:
            # Добавляем тестовые города
            cities_data = [
                {'name': 'Москва'},
                {'name': 'Санкт-Петербург'},
                {'name': 'Новосибирск'}
            ]
            for city_data in cities_data:
                city = City(**city_data)
                db.session.add(city)
            
            db.session.commit()
            
            # Добавляем тестовые объекты
            moscow = City.query.filter_by(name='Москва').first()
            spb = City.query.filter_by(name='Санкт-Петербург').first()
            
            objects_data = [
                {'city_id': moscow.id, 'name': 'Объект 1 в Москве'},
                {'city_id': moscow.id, 'name': 'Объект 2 в Москве'},
                {'city_id': spb.id, 'name': 'Объект 1 в СПб'},
                {'city_id': spb.id, 'name': 'Объект 2 в СПб'}
            ]
            for obj_data in objects_data:
                obj = Object(**obj_data)
                db.session.add(obj)
            
            db.session.commit()
        
        if ViolationCategory.query.count() == 0:
            # Добавляем тестовые категории нарушений
            categories_data = [
                {'name': 'Безопасность'},
                {'name': 'Санитария'},
                {'name': 'Пожарная безопасность'}
            ]
            for cat_data in categories_data:
                category = ViolationCategory(**cat_data)
                db.session.add(category)
            
            db.session.commit()
            
            # Добавляем тестовые нарушения
            safety = ViolationCategory.query.filter_by(name='Безопасность').first()
            sanitation = ViolationCategory.query.filter_by(name='Санитария').first()
            
            violations_data = [
                {'category_id': safety.id, 'name': 'Отсутствие ограждения'},
                {'category_id': safety.id, 'name': 'Неисправное освещение'},
                {'category_id': sanitation.id, 'name': 'Загрязнение территории'},
                {'category_id': sanitation.id, 'name': 'Отсутствие урн'}
            ]
            for viol_data in violations_data:
                violation = Violation(**viol_data)
                db.session.add(violation)

            db.session.commit()

        if User.query.count() == 0:
            # Добавляем тестовых пользователей
            users_data = [
                {'first_name': 'Иван', 'last_name': 'Иванов', 'tg_id': 123456789, 'secret_key': User.generate_secret_key()},
                {'first_name': 'Мария', 'last_name': 'Петрова', 'tg_id': 987654321, 'secret_key': User.generate_secret_key()},
                {'first_name': 'Алексей', 'last_name': 'Сидоров', 'tg_id': 555123456, 'secret_key': User.generate_secret_key()}
            ]
            for user_data in users_data:
                user = User(**user_data)
                db.session.add(user)

            db.session.commit()


def _add_missing_btxid_columns():
    """Добавление недостающих колонок btxid в существующие таблицы"""
    try:
        # Список таблиц и колонок для проверки
        tables_to_check = [
            ('cities', 'name'),
            ('objects', 'name'),
            ('violation_categories', 'name'),
            ('violations', 'name'),
            ('users', 'secret_key')
        ]
        
        for table_name, after_column in tables_to_check:
            try:
                # Проверяем существование колонки btxid
                with db.engine.connect() as conn:
                    result = conn.execute(text(
                        f"SELECT COUNT(*) as cnt FROM information_schema.COLUMNS "
                        f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}' AND COLUMN_NAME = 'btxid'"
                    ))
                    column_exists = result.fetchone()[0] > 0
                    
                    if not column_exists:
                        # Добавляем колонку btxid
                        conn.execute(text(
                            f"ALTER TABLE {table_name} ADD COLUMN btxid INT NULL DEFAULT NULL AFTER {after_column}"
                        ))
                        conn.commit()
                        print(f"Added btxid column to {table_name}")
            except Exception as e:
                # Игнорируем ошибки, если колонка уже существует или таблица не существует
                error_msg = str(e)
                if 'Duplicate column name' not in error_msg and "doesn't exist" not in error_msg:
                    print(f"Warning: Could not add btxid to {table_name}: {e}")
    except Exception as e:
        # Игнорируем ошибки миграции, чтобы не блокировать запуск приложения
        print(f"Warning: Could not check/add btxid columns: {e}")
