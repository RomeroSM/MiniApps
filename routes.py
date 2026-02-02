import os
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from database import db
from models import City, Object, ViolationCategory, Violation, FormSubmission, User
from config import Config
from telegram_validation import validate_telegram_webapp_data

api = Blueprint('api', __name__)


def check_api_token():
    """Проверка API токена для авторизации"""
    # Если токен не установлен в конфигурации, авторизация отключена
    if not Config.API_TOKEN:
        return None
    
    # Получаем токен из параметров запроса (query параметр имеет приоритет)
    token = request.args.get('token')
    
    # Если токен не найден в query параметрах, проверяем body
    if not token:
        try:
            # Пытаемся получить из JSON
            if request.is_json:
                data = request.get_json(silent=True) or {}
                token = data.get('token') if data else None
            # Если не JSON, пытаемся получить из form-data
            if not token:
                try:
                    token = request.form.get('token')
                except Exception:
                    pass
        except Exception:
            # Если не удается прочитать тело запроса, игнорируем ошибку
            pass
    
    if not token:
        return jsonify({
            'success': False,
            'error': 'API token is required. Provide token as query parameter (?token=...) or in request body.'
        }), 401
    
    if token != Config.API_TOKEN:
        return jsonify({
            'success': False,
            'error': 'Invalid API token'
        }), 401
    
    return None


# Применяем проверку токена ко всем запросам к API
@api.before_request
def before_request():
    """Проверка токена перед обработкой каждого запроса"""
    # Исключаем публичные endpoints из проверки токена - они используются из Telegram WebApp
    # и имеют свою проверку через Telegram initData
    public_endpoints = [
        '/users/check-access',  # Проверка доступа пользователей Telegram
        '/cities',              # GET - загрузка списка городов
        '/objects',              # GET - загрузка объектов по городу
        '/violation-categories', # GET - загрузка категорий нарушений
        '/violations',          # GET - загрузка нарушений по категории
        '/submit'               # POST - отправка формы (проверяется через Telegram initData)
    ]
    
    # Проверяем, является ли текущий путь публичным endpoint
    is_public = any(request.path.endswith(endpoint) for endpoint in public_endpoints)
    
    # Для GET запросов к справочникам и POST к /submit - пропускаем проверку токена
    # (они проверяются через Telegram initData в самих функциях)
    if is_public:
        return None
    
    error_response = check_api_token()
    if error_response:
        return error_response


def get_request_data():
    """Безопасное получение данных из запроса (JSON, form-data или query параметры)"""
    data = {}
    
    # Сначала получаем данные из query параметров
    if request.args:
        for key in request.args.keys():
            # request.args может возвращать списки, берем первое значение
            value = request.args.get(key)
            if value is not None:
                data[key] = value
    
    # Затем пытаемся получить данные из тела запроса (JSON или form-data)
    try:
        # Пытаемся получить JSON данные
        if request.is_json or (request.content_type and 'application/json' in request.content_type):
            json_data = request.get_json(silent=True)
            if json_data:
                # Объединяем с query параметрами (данные из тела имеют приоритет)
                data.update(json_data)
                return data
    except Exception:
        pass
    
    try:
        # Если не JSON, пытаемся получить form-data
        # Проверяем Content-Type для form-data
        if request.content_type and ('application/x-www-form-urlencoded' in request.content_type or 'multipart/form-data' in request.content_type):
            if request.form:
                # Объединяем с query параметрами (данные из формы имеют приоритет)
                for key, value in request.form.items():
                    data[key] = value
    except Exception:
        pass
    
    # Возвращаем объединенные данные (query параметры + тело запроса)
    return data


def allowed_file(filename):
    """Проверка имени файла (типы не ограничиваем)"""
    return bool(filename)


def is_authorized_telegram_user(telegram_user_id):
    """Проверяет, есть ли пользователь с данным tg_id в базе данных"""
    import logging
    logger = logging.getLogger(__name__)
    
    if not telegram_user_id:
        logger.warning(f"is_authorized_telegram_user: telegram_user_id is None or empty")
        return False

    logger.info(f"is_authorized_telegram_user: checking telegram_user_id={telegram_user_id}, type={type(telegram_user_id)}")
    
    user = User.query.filter_by(tg_id=telegram_user_id).first()
    
    if user:
        logger.info(f"is_authorized_telegram_user: user found - id={user.id}, tg_id={user.tg_id}, type(tg_id)={type(user.tg_id)}")
    else:
        logger.warning(f"is_authorized_telegram_user: user NOT found for telegram_user_id={telegram_user_id}")
        # Логируем все пользователей в БД для отладки
        all_users = User.query.all()
        logger.info(f"is_authorized_telegram_user: all users in DB: {[(u.id, u.tg_id, type(u.tg_id)) for u in all_users]}")
    
    return user is not None


@api.route('/cities', methods=['GET'])
def get_cities():
    """Получить список всех городов"""
    try:
        cities = City.query.order_by(City.name).all()
        return jsonify({
            'success': True,
            'data': [city.to_dict() for city in cities]
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/cities', methods=['POST'])
def create_city():
    """Создать новый город"""
    try:
        data = get_request_data()

        required_fields = ['name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Field {field} is required'
                }), 400

        # Проверка, что город с таким именем еще не существует
        existing_city = City.query.filter_by(name=data.get('name')).first()
        if existing_city:
            return jsonify({
                'success': False,
                'error': 'City with this name already exists'
            }), 400

        # Создание нового города
        city = City(
            name=data.get('name').strip(),
            btxid=int(data.get('btxid')) if data.get('btxid') else None
        )

        db.session.add(city)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'City created successfully',
            'data': city.to_dict()
        }), 201

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/cities/<int:city_id>', methods=['PUT'])
def update_city(city_id):
    """Обновить город"""
    try:
        city = City.query.get(city_id)
        if not city:
            return jsonify({
                'success': False,
                'error': 'City not found'
            }), 404

        data = get_request_data()

        # Обновление полей
        if 'name' in data:
            # Проверка уникальности имени
            existing_city = City.query.filter_by(name=data.get('name')).first()
            if existing_city and existing_city.id != city_id:
                return jsonify({
                    'success': False,
                    'error': 'City with this name already exists'
                }), 400
            city.name = data.get('name').strip()

        if 'btxid' in data:
            city.btxid = int(data.get('btxid')) if data.get('btxid') else None

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'City updated successfully',
            'data': city.to_dict()
        }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/objects', methods=['GET'])
def get_objects():
    """Получить список объектов по городу (city_id — btxid города в Bitrix24)."""
    try:
        city_id = request.args.get('city_id', type=int)
        if not city_id:
            return jsonify({
                'success': False,
                'error': 'city_id parameter is required'
            }), 400
        city = City.query.filter_by(btxid=city_id).first()
        if not city:
            return jsonify({
                'success': False,
                'error': 'City not found'
            }), 400
        objects = Object.query.filter_by(city_id=city.id).order_by(Object.name).all()
        return jsonify({
            'success': True,
            'data': [obj.to_dict() for obj in objects]
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/objects', methods=['POST'])
def create_object():
    """Создать новый объект"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        data = get_request_data()
        logger.info(f"create_object: received data: {data}, request.args: {dict(request.args)}, request.form: {dict(request.form)}")

        required_fields = ['city_id', 'name']
        for field in required_fields:
            value = data.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                logger.warning(f"create_object: missing or empty field '{field}', data: {data}")
                return jsonify({
                    'success': False,
                    'error': f'Field {field} is required'
                }), 400

        city_id = int(data.get('city_id'))
        
        # Проверка существования города
        city = City.query.get(city_id)
        if not city:
            return jsonify({
                'success': False,
                'error': 'Invalid city_id: city not found'
            }), 400

        # Создание нового объекта
        obj = Object(
            city_id=city_id,
            name=data.get('name').strip(),
            btxid=int(data.get('btxid')) if data.get('btxid') else None,
            state=data.get('state') or None
        )

        db.session.add(obj)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Object created successfully',
            'data': obj.to_dict()
        }), 201

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/objects/<int:object_id>', methods=['PUT'])
def update_object(object_id):
    """Обновить объект"""
    try:
        obj = Object.query.get(object_id)
        if not obj:
            return jsonify({
                'success': False,
                'error': 'Object not found'
            }), 404

        data = get_request_data()

        # Обновление полей
        if 'city_id' in data:
            city_id = int(data.get('city_id'))
            city = City.query.get(city_id)
            if not city:
                return jsonify({
                    'success': False,
                    'error': 'Invalid city_id: city not found'
                }), 400
            obj.city_id = city_id

        if 'name' in data:
            obj.name = data.get('name').strip()

        if 'btxid' in data:
            obj.btxid = int(data.get('btxid')) if data.get('btxid') else None

        if 'state' in data:
            obj.state = data.get('state') or None

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Object updated successfully',
            'data': obj.to_dict()
        }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/violation-categories', methods=['GET'])
def get_violation_categories():
    """Получить список категорий нарушений"""
    try:
        categories = ViolationCategory.query.order_by(ViolationCategory.name).all()
        return jsonify({
            'success': True,
            'data': [cat.to_dict() for cat in categories]
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/violation-categories', methods=['POST'])
def create_violation_category():
    """Создать новую категорию нарушений"""
    try:
        data = get_request_data()

        required_fields = ['name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Field {field} is required'
                }), 400

        # Проверка, что категория с таким именем еще не существует
        existing_category = ViolationCategory.query.filter_by(name=data.get('name')).first()
        if existing_category:
            return jsonify({
                'success': False,
                'error': 'Violation category with this name already exists'
            }), 400

        # Создание новой категории нарушений
        category = ViolationCategory(
            name=data.get('name').strip(),
            btxid=int(data.get('btxid')) if data.get('btxid') else None
        )

        db.session.add(category)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Violation category created successfully',
            'data': category.to_dict()
        }), 201

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/violation-categories/<int:category_id>', methods=['PUT'])
def update_violation_category(category_id):
    """Обновить категорию нарушений"""
    try:
        category = ViolationCategory.query.get(category_id)
        if not category:
            return jsonify({
                'success': False,
                'error': 'Violation category not found'
            }), 404

        data = get_request_data()

        # Обновление полей
        if 'name' in data:
            # Проверка уникальности имени
            existing_category = ViolationCategory.query.filter_by(name=data.get('name')).first()
            if existing_category and existing_category.id != category_id:
                return jsonify({
                    'success': False,
                    'error': 'Violation category with this name already exists'
                }), 400
            category.name = data.get('name').strip()

        if 'btxid' in data:
            category.btxid = int(data.get('btxid')) if data.get('btxid') else None

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Violation category updated successfully',
            'data': category.to_dict()
        }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/violations', methods=['GET'])
def get_violations():
    """Получить список нарушений по категории (category_id — btxid категории в Bitrix24)."""
    try:
        category_id = request.args.get('category_id', type=int)
        if not category_id:
            return jsonify({
                'success': False,
                'error': 'category_id parameter is required'
            }), 400
        category = ViolationCategory.query.filter_by(btxid=category_id).first()
        if not category:
            return jsonify({
                'success': False,
                'error': 'Category not found'
            }), 400
        violations = Violation.query.filter_by(category_id=category.id).order_by(Violation.name).all()
        return jsonify({
            'success': True,
            'data': [viol.to_dict() for viol in violations]
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/violations', methods=['POST'])
def create_violation():
    """Создать новое нарушение"""
    try:
        data = get_request_data()

        required_fields = ['category_id', 'name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Field {field} is required'
                }), 400

        category_id = int(data.get('category_id'))
        
        # Проверка существования категории
        category = ViolationCategory.query.get(category_id)
        if not category:
            return jsonify({
                'success': False,
                'error': 'Invalid category_id: violation category not found'
            }), 400

        # Создание нового нарушения
        violation = Violation(
            category_id=category_id,
            name=data.get('name').strip(),
            btxid=int(data.get('btxid')) if data.get('btxid') else None,
            state=data.get('state') or None
        )

        db.session.add(violation)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Violation created successfully',
            'data': violation.to_dict()
        }), 201

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/violations/<int:violation_id>', methods=['PUT'])
def update_violation(violation_id):
    """Обновить нарушение"""
    try:
        violation = Violation.query.get(violation_id)
        if not violation:
            return jsonify({
                'success': False,
                'error': 'Violation not found'
            }), 404

        data = get_request_data()

        # Обновление полей
        if 'category_id' in data:
            category_id = int(data.get('category_id'))
            category = ViolationCategory.query.get(category_id)
            if not category:
                return jsonify({
                    'success': False,
                    'error': 'Invalid category_id: violation category not found'
                }), 400
            violation.category_id = category_id

        if 'name' in data:
            violation.name = data.get('name').strip()

        if 'btxid' in data:
            violation.btxid = int(data.get('btxid')) if data.get('btxid') else None

        if 'state' in data:
            violation.state = data.get('state') or None

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Violation updated successfully',
            'data': violation.to_dict()
        }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/submit', methods=['POST'])
def submit_form():
    """Сохранение данных формы"""
    try:
        # Валидация Telegram WebApp данных (опционально, можно отключить для тестирования)
        init_data = request.headers.get('X-Telegram-Init-Data')
        if init_data and Config.TELEGRAM_BOT_TOKEN:
            if not validate_telegram_webapp_data(init_data, Config.TELEGRAM_BOT_TOKEN):
                return jsonify({
                    'success': False,
                    'error': 'Invalid Telegram WebApp data'
                }), 401

        # Получение user_id из Telegram данных (если есть)
        import logging
        logger = logging.getLogger(__name__)
        telegram_user_id = None
        if init_data:
            try:
                from urllib.parse import parse_qs, unquote
                parsed_data = parse_qs(unquote(init_data))
                logger.info(f"submit_form: parsed_data keys: {parsed_data.keys()}")
                if 'user' in parsed_data:
                    import json
                    user_data = json.loads(parsed_data['user'][0])
                    telegram_user_id = user_data.get('id')
                    logger.info(f"submit_form: extracted telegram_user_id={telegram_user_id}, type={type(telegram_user_id)}, user_data={user_data}")
            except Exception as e:
                logger.error(f"submit_form: error extracting telegram_user_id: {e}", exc_info=True)
                pass

        # Проверка авторизации пользователя
        if telegram_user_id and not is_authorized_telegram_user(telegram_user_id):
            logger.warning(f"submit_form: access denied for telegram_user_id={telegram_user_id}")
            return jsonify({
                'success': False,
                'error': 'Unauthorized: User is not registered in the system'
            }), 403
        elif telegram_user_id:
            logger.info(f"submit_form: access granted for telegram_user_id={telegram_user_id}")

        # Получение данных формы
        data = request.form

        # Валидация обязательных полей
        required_fields = ['city_id', 'object_id', 'violation_category_id', 'violation_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Field {field} is required'
                }), 400

        city_id = int(data.get('city_id'))  # btxid города в Bitrix24
        object_id = int(data.get('object_id'))  # btxid объекта
        violation_category_id = int(data.get('violation_category_id'))  # btxid категории
        violation_id = int(data.get('violation_id'))  # btxid нарушения
        comment = data.get('comment', '').strip()

        # Проверка существования связанных записей (по btxid)
        city = City.query.filter_by(btxid=city_id).first()
        if not city:
            return jsonify({
                'success': False,
                'error': 'Invalid city_id'
            }), 400

        obj = Object.query.filter_by(btxid=object_id).first()
        if not obj or obj.city_id != city.id:
            return jsonify({
                'success': False,
                'error': 'Invalid object_id for selected city'
            }), 400

        category = ViolationCategory.query.filter_by(btxid=violation_category_id).first()
        if not category:
            return jsonify({
                'success': False,
                'error': 'Invalid violation_category_id'
            }), 400

        violation = Violation.query.filter_by(btxid=violation_id).first()
        if not violation or violation.category_id != category.id:
            return jsonify({
                'success': False,
                'error': 'Invalid violation_id for selected category'
            }), 400

        # Обработка загрузки файлов
        file_path = None
        files = request.files.getlist('files') or request.files.getlist('file')
        files = [f for f in files if f and f.filename]

        if files:
            if len(files) > 5:
                return jsonify({
                    'success': False,
                    'error': 'Maximum 5 files are allowed'
                }), 400

            saved_files = []
            for file in files:
                if not allowed_file(file.filename):
                    return jsonify({
                        'success': False,
                        'error': 'Invalid file'
                    }), 400

                # Проверка размера файла
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)

                if file_size > Config.MAX_FILE_SIZE:
                    return jsonify({
                        'success': False,
                        'error': f'File size exceeds maximum allowed size of {Config.MAX_FILE_SIZE / 1024 / 1024} MB'
                    }), 400

                # Сохранение файла
                filename = secure_filename(file.filename)
                # Добавляем timestamp для уникальности
                import time
                timestamp = int(time.time())
                filename = f"{timestamp}_{filename}"

                # Создаем папку uploads если её нет
                os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

                file_full_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                file.save(file_full_path)
                saved_files.append(filename)

            # Сохраняем список файлов в БД
            import json
            file_path = json.dumps(saved_files)

        # Создание записи (city_id хранит btxid города)
        submission = FormSubmission(
            city_id=city_id,
            object_id=object_id,
            violation_category_id=violation_category_id,
            violation_id=violation_id,
            comment=comment if comment else None,
            file_path=file_path,
            telegram_user_id=telegram_user_id
        )

        db.session.add(submission)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Form submitted successfully',
            'data': submission.to_dict()
        }), 201

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/users', methods=['GET'])
def get_users():
    """Получить список всех пользователей (без секретных ключей)"""
    try:
        users = User.query.all()
        return jsonify({
            'success': True,
            'data': [{
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'tg_id': user.tg_id,
                'btxid': user.btxid,
                'created_at': user.created_at.isoformat() if user.created_at else None
            } for user in users]
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/users', methods=['POST'])
def create_user():
    """Создать нового пользователя"""
    try:
        data = get_request_data()

        required_fields = ['first_name', 'last_name', 'tg_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Field {field} is required'
                }), 400

        # Проверка, что пользователь с таким tg_id еще не существует
        existing_user = User.query.filter_by(tg_id=data.get('tg_id')).first()
        if existing_user:
            return jsonify({
                'success': False,
                'error': 'User with this tg_id already exists'
            }), 400

        # Создание нового пользователя с генерацией секретного ключа
        user = User(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            tg_id=int(data.get('tg_id')),
            secret_key=User.generate_secret_key(),
            btxid=int(data.get('btxid')) if data.get('btxid') else None
        )

        db.session.add(user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'data': {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'tg_id': user.tg_id,
                'btxid': user.btxid,
                'created_at': user.created_at.isoformat(),
                'secret_key': user.secret_key  # Возвращаем сгенерированный ключ
            }
        }), 201

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Обновить пользователя"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        data = get_request_data()

        # Обновление полей
        if 'first_name' in data:
            user.first_name = data.get('first_name').strip()

        if 'last_name' in data:
            user.last_name = data.get('last_name').strip()

        if 'tg_id' in data:
            # Проверка уникальности tg_id
            existing_user = User.query.filter_by(tg_id=int(data.get('tg_id'))).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({
                    'success': False,
                    'error': 'User with this tg_id already exists'
                }), 400
            user.tg_id = int(data.get('tg_id'))

        if 'btxid' in data:
            user.btxid = int(data.get('btxid')) if data.get('btxid') else None

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'data': user.to_dict()
        }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/users/check-access', methods=['POST'])
def check_user_access():
    """Проверить доступ пользователя по tg_id или из Telegram initData"""
    try:
        data = get_request_data()

        # Попробовать получить tg_id из тела запроса
        tg_id = data.get('tg_id')

        # Если tg_id не передан в теле, попробовать извлечь из Telegram initData
        if not tg_id:
            init_data = request.headers.get('X-Telegram-Init-Data')
            if init_data and Config.TELEGRAM_BOT_TOKEN:
                if not validate_telegram_webapp_data(init_data, Config.TELEGRAM_BOT_TOKEN):
                    return jsonify({
                        'success': False,
                        'error': 'Invalid Telegram WebApp data'
                    }), 401

                try:
                    from urllib.parse import parse_qs, unquote
                    parsed_data = parse_qs(unquote(init_data))
                    if 'user' in parsed_data:
                        import json
                        user_data = json.loads(parsed_data['user'][0])
                        tg_id = user_data.get('id')
                except:
                    pass

        if not tg_id:
            return jsonify({
                'success': False,
                'error': 'tg_id is required'
            }), 400

        user = User.query.filter_by(tg_id=int(tg_id)).first()
        if user:
            return jsonify({
                'success': True,
                'authorized': True,
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({
                'success': True,
                'authorized': False,
                'message': 'User not found in the system'
            }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/submissions', methods=['GET'])
def get_submissions():
    """Получить список отправленных форм (опционально, для администрирования)"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        submissions = FormSubmission.query.order_by(FormSubmission.created_at.desc()).limit(limit).offset(offset).all()
        
        return jsonify({
            'success': True,
            'data': [sub.to_dict() for sub in submissions],
            'count': len(submissions)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/uploads/<filename>', methods=['GET'])
def download_file(filename):
    """Скачать загруженный файл"""
    try:
        return send_from_directory(Config.UPLOAD_FOLDER, filename)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'File not found'
        }), 404

