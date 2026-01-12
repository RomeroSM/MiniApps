import os
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from database import db
from models import City, Object, ViolationCategory, Violation, FormSubmission
from config import Config
from telegram_validation import validate_telegram_webapp_data

api = Blueprint('api', __name__)


def allowed_file(filename):
    """Проверка разрешенного расширения файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


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


@api.route('/objects', methods=['GET'])
def get_objects():
    """Получить список объектов по городу"""
    try:
        city_id = request.args.get('city_id', type=int)
        if not city_id:
            return jsonify({
                'success': False,
                'error': 'city_id parameter is required'
            }), 400
        
        objects = Object.query.filter_by(city_id=city_id).order_by(Object.name).all()
        return jsonify({
            'success': True,
            'data': [obj.to_dict() for obj in objects]
        }), 200
    except Exception as e:
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


@api.route('/violations', methods=['GET'])
def get_violations():
    """Получить список нарушений по категории"""
    try:
        category_id = request.args.get('category_id', type=int)
        if not category_id:
            return jsonify({
                'success': False,
                'error': 'category_id parameter is required'
            }), 400
        
        violations = Violation.query.filter_by(category_id=category_id).order_by(Violation.name).all()
        return jsonify({
            'success': True,
            'data': [viol.to_dict() for viol in violations]
        }), 200
    except Exception as e:
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
        
        city_id = int(data.get('city_id'))
        object_id = int(data.get('object_id'))
        violation_category_id = int(data.get('violation_category_id'))
        violation_id = int(data.get('violation_id'))
        comment = data.get('comment', '').strip()
        
        # Проверка существования связанных записей
        if not City.query.get(city_id):
            return jsonify({
                'success': False,
                'error': 'Invalid city_id'
            }), 400
        
        if not Object.query.filter_by(id=object_id, city_id=city_id).first():
            return jsonify({
                'success': False,
                'error': 'Invalid object_id for selected city'
            }), 400
        
        if not ViolationCategory.query.get(violation_category_id):
            return jsonify({
                'success': False,
                'error': 'Invalid violation_category_id'
            }), 400
        
        if not Violation.query.filter_by(id=violation_id, category_id=violation_category_id).first():
            return jsonify({
                'success': False,
                'error': 'Invalid violation_id for selected category'
            }), 400
        
        # Обработка загрузки файла
        file_path = None
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename and allowed_file(file.filename):
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
                
                file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                file.save(file_path)
                file_path = filename  # Сохраняем только имя файла в БД
        
        # Получение user_id из Telegram данных (если есть)
        telegram_user_id = None
        if init_data:
            try:
                from urllib.parse import parse_qs, unquote
                parsed_data = parse_qs(unquote(init_data))
                if 'user' in parsed_data:
                    import json
                    user_data = json.loads(parsed_data['user'][0])
                    telegram_user_id = user_data.get('id')
            except:
                pass
        
        # Создание записи
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

