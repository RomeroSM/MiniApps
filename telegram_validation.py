import hashlib
import hmac
from urllib.parse import parse_qs, unquote


def validate_telegram_webapp_data(init_data: str, bot_token: str) -> bool:
    """
    Валидация данных Telegram WebApp
    
    Args:
        init_data: Строка initData из Telegram WebApp
        bot_token: Токен Telegram бота
    
    Returns:
        True если данные валидны, False в противном случае
    """
    try:
        # Парсим данные
        parsed_data = parse_qs(unquote(init_data))
        
        # Извлекаем hash и остальные данные
        received_hash = parsed_data.get('hash', [None])[0]
        if not received_hash:
            return False
        
        # Удаляем hash из данных для проверки
        data_check_string = []
        for key in sorted(parsed_data.keys()):
            if key != 'hash':
                data_check_string.append(f"{key}={parsed_data[key][0]}")
        
        data_check_string = '\n'.join(data_check_string)
        
        # Создаем секретный ключ
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        # Вычисляем hash
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Сравниваем hash
        return calculated_hash == received_hash
        
    except Exception as e:
        print(f"Error validating Telegram data: {e}")
        return False


