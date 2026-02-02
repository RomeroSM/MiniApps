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
                # Добавление колонки state в objects при необходимости
                _add_missing_object_state_column()
                # Добавление колонки state в violations при необходимости
                _add_missing_violation_state_column()
                # Увеличение размера file_path в form_submissions при необходимости
                _ensure_file_path_text()
                # form_submissions.city_id: привязка к cities.btxid вместо cities.id
                _migrate_form_submissions_city_to_btxid()
                # form_submissions.object_id, violation_category_id, violation_id: привязка к *.btxid вместо *.id
                _migrate_form_submissions_object_category_violation_to_btxid()
                
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


def _add_missing_object_state_column():
    """Добавление колонки state в таблицу objects при отсутствии"""
    try:
        with db.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'objects' AND COLUMN_NAME = 'state'"
            ))
            column_exists = result.fetchone()[0] > 0
            if not column_exists:
                conn.execute(text(
                    "ALTER TABLE objects ADD COLUMN state VARCHAR(100) NULL DEFAULT NULL AFTER btxid"
                ))
                conn.commit()
                print("Added state column to objects")
    except Exception as e:
        error_msg = str(e)
        if 'Duplicate column name' not in error_msg and "doesn't exist" not in error_msg:
            print(f"Warning: Could not add state column to objects: {e}")


def _add_missing_violation_state_column():
    """Добавление колонки state в таблицу violations при отсутствии"""
    try:
        with db.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'violations' AND COLUMN_NAME = 'state'"
            ))
            column_exists = result.fetchone()[0] > 0
            if not column_exists:
                conn.execute(text(
                    "ALTER TABLE violations ADD COLUMN state VARCHAR(100) NULL DEFAULT NULL AFTER btxid"
                ))
                conn.commit()
                print("Added state column to violations")
    except Exception as e:
        error_msg = str(e)
        if 'Duplicate column name' not in error_msg and "doesn't exist" not in error_msg:
            print(f"Warning: Could not add state column to violations: {e}")


def _ensure_file_path_text():
    """Увеличение размера file_path в form_submissions до TEXT при необходимости"""
    try:
        with db.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT DATA_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'form_submissions' AND COLUMN_NAME = 'file_path'"
            ))
            row = result.fetchone()
            if not row:
                return

            data_type = (row[0] or '').lower()
            if data_type not in ('text', 'mediumtext', 'longtext'):
                conn.execute(text(
                    "ALTER TABLE form_submissions MODIFY COLUMN file_path TEXT NULL"
                ))
                conn.commit()
                print("Updated form_submissions.file_path to TEXT")
    except Exception as e:
        # Игнорируем ошибки миграции, чтобы не блокировать запуск приложения
        print(f"Warning: Could not update file_path column type: {e}")


def _migrate_form_submissions_city_to_btxid():
    """Перевод form_submissions.city_id с ссылки на cities.id на cities.btxid."""
    try:
        with db.engine.connect() as conn:
            # Проверяем, что FK ещё ссылается на cities.id (миграция не выполнялась)
            r = conn.execute(text(
                "SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'form_submissions' "
                "AND COLUMN_NAME = 'city_id' AND REFERENCED_TABLE_NAME = 'cities' AND REFERENCED_COLUMN_NAME = 'id'"
            ))
            row = r.fetchone()
            if not row:
                # Уже мигрировано или другой вариант схемы
                return
            fk_name = row[0]

            # Уникальный индекс на cities.btxid (для FK)
            r2 = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cities' AND COLUMN_NAME = 'btxid' AND NON_UNIQUE = 0"
            ))
            if r2.fetchone()[0] == 0:
                conn.execute(text("ALTER TABLE cities ADD UNIQUE INDEX cities_btxid_unique (btxid)"))
                conn.commit()

            # Разрешить NULL в city_id (для городов без btxid)
            conn.execute(text("ALTER TABLE form_submissions MODIFY COLUMN city_id INT NULL"))
            conn.commit()

            # Обновить значения: city_id = btxid города (где city_id раньше был id)
            conn.execute(text(
                "UPDATE form_submissions fs "
                "INNER JOIN cities c ON c.id = fs.city_id "
                "SET fs.city_id = c.btxid"
            ))
            conn.commit()

            # Удалить старый FK
            conn.execute(text(f"ALTER TABLE form_submissions DROP FOREIGN KEY `{fk_name}`"))
            conn.commit()

            # Добавить новый FK на cities.btxid
            conn.execute(text(
                "ALTER TABLE form_submissions ADD CONSTRAINT form_submissions_city_btxid_fk "
                "FOREIGN KEY (city_id) REFERENCES cities(btxid) ON DELETE RESTRICT"
            ))
            conn.commit()
            print("Migrated form_submissions.city_id to reference cities.btxid")
    except Exception as e:
        print(f"Warning: Could not migrate form_submissions.city_id to btxid: {e}")


def _migrate_form_submissions_object_category_violation_to_btxid():
    """Перевод form_submissions.object_id, violation_category_id, violation_id на ссылки на *.btxid."""
    refs = [
        ('object_id', 'objects', 'objects_btxid_unique', 'form_submissions_object_btxid_fk'),
        ('violation_category_id', 'violation_categories', 'violation_categories_btxid_unique', 'form_submissions_violation_category_btxid_fk'),
        ('violation_id', 'violations', 'violations_btxid_unique', 'form_submissions_violation_btxid_fk'),
    ]
    for col, table, unique_idx, new_fk_name in refs:
        try:
            with db.engine.connect() as conn:
                r = conn.execute(text(
                    "SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'form_submissions' "
                    "AND COLUMN_NAME = :col AND REFERENCED_TABLE_NAME = :tbl AND REFERENCED_COLUMN_NAME = 'id'"
                ), {"col": col, "tbl": table})
                row = r.fetchone()
                if not row:
                    continue
                fk_name = row[0]

                # Уникальный индекс на ref.btxid
                r2 = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.STATISTICS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :tbl AND COLUMN_NAME = 'btxid' AND NON_UNIQUE = 0"
                ), {"tbl": table})
                if r2.fetchone()[0] == 0:
                    conn.execute(text(f"ALTER TABLE {table} ADD UNIQUE INDEX {unique_idx} (btxid)"))
                    conn.commit()

                conn.execute(text(f"ALTER TABLE form_submissions MODIFY COLUMN {col} INT NULL"))
                conn.commit()

                # UPDATE: col = btxid из ref по текущему id
                conn.execute(text(
                    f"UPDATE form_submissions fs "
                    f"INNER JOIN {table} r ON r.id = fs.{col} "
                    f"SET fs.{col} = r.btxid"
                ))
                conn.commit()

                conn.execute(text(f"ALTER TABLE form_submissions DROP FOREIGN KEY `{fk_name}`"))
                conn.commit()

                conn.execute(text(
                    f"ALTER TABLE form_submissions ADD CONSTRAINT {new_fk_name} "
                    f"FOREIGN KEY ({col}) REFERENCES {table}(btxid) ON DELETE RESTRICT"
                ))
                conn.commit()
                print(f"Migrated form_submissions.{col} to reference {table}.btxid")
        except Exception as e:
            print(f"Warning: Could not migrate form_submissions.{col} to btxid: {e}")
