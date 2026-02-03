import base64
import json
import logging
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from app.config import Config

logger = logging.getLogger(__name__)


class Bitrix24Client:
    """Клиент для работы с Bitrix24 REST API через POST-запросы"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Инициализация клиента Bitrix24
        
        Args:
            webhook_url: URL webhook Bitrix24. Если не указан, берется из Config
        """
        self.webhook_url = webhook_url or Config.BITRIX_WEBHOOK_URL
        if not self.webhook_url:
            raise ValueError("BITRIX_WEBHOOK_URL не указан в конфигурации")
        
        # Убеждаемся, что URL не заканчивается на / (метод будет добавлен позже)
        # Удаляем метод из URL, если он там есть (например, /lists.field.get/)
        if '/lists.field.get' in self.webhook_url or '/crm.' in self.webhook_url:
            # Удаляем все после последнего / перед методом
            parts = self.webhook_url.split('/rest/')
            if len(parts) == 2:
                rest_part = parts[1].split('/')
                if len(rest_part) >= 2:
                    # Берем только USER_ID и CODE, убираем метод
                    self.webhook_url = f"{parts[0]}/rest/{rest_part[0]}/{rest_part[1]}"
                    logger.warning(f"Webhook URL очищен от метода: {self.webhook_url}")
        
        # Удаляем завершающий / если есть
        self.webhook_url = self.webhook_url.rstrip('/')
        logger.info(f"Webhook URL: {self.webhook_url}")
        
        self.timeout = 30
        self.max_retries = 3
        self.retry_delay = 1
    
    def _call_method(self, method: str, params: Optional[Dict] = None, return_full_response: bool = False) -> Any:
        """
        Вызов метода Bitrix24 REST API через POST-запрос
        
        Args:
            method: Название метода API (например, 'crm.type.list')
            params: Параметры запроса
            return_full_response: Если True, вернуть полный ответ (result + next и др.), иначе только result
            
        Returns:
            Ответ от API (result или полный dict при return_full_response=True)
            
        Raises:
            Exception: При ошибке выполнения запроса
        """
        if params is None:
            params = {}
        
        # Формируем URL с методом: webhook_url + /method
        request_url = f"{self.webhook_url}/{method}"
        
        # В теле запроса только параметры (без method)
        payload = params
        
        # Логируем запрос для отладки
        logger.info(f"Bitrix24 API request: Method={method}, Params={params}")
        logger.debug(f"Bitrix24 API request: URL={request_url}")
        logger.debug(f"Bitrix24 API request payload: {payload}")
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    request_url,
                    json=payload,
                    timeout=self.timeout
                )
                
                # Логируем статус ответа
                logger.debug(f"Bitrix24 API response status: {response.status_code}")
                
                # Проверяем статус HTTP
                if response.status_code == 400:
                    try:
                        error_data = response.json()
                        error_text = str(error_data)
                    except:
                        error_text = response.text[:500] if response.text else "No response body"
                    
                    logger.error(f"Bitrix24 API 400 error. URL: {request_url}")
                    logger.error(f"Request payload: {payload}")
                    logger.error(f"Response: {error_text}")
                    raise Exception(f"Bitrix24 API 400 error: Bad Request. URL: {request_url}. Payload: {payload}. Response: {error_text}")
                
                if response.status_code == 404:
                    try:
                        error_data = response.json()
                        error_text = str(error_data)
                    except:
                        error_text = response.text[:500] if response.text else "No response body"
                    
                    logger.error(f"Bitrix24 API 404 error. URL: {request_url}")
                    logger.error(f"Request payload: {payload}")
                    logger.error(f"Response: {error_text}")
                    raise Exception(f"Bitrix24 API 404 error: Method '{method}' not found. URL: {request_url}. Response: {error_text}")
                
                response.raise_for_status()
                
                data = response.json()
                
                # Логируем ответ для отладки (первые 500 символов)
                logger.debug(f"Bitrix24 API response: {str(data)[:500]}")
                
                # Проверка на ошибки в ответе Bitrix24
                if 'error' in data:
                    error_msg = data.get('error_description', data.get('error', 'Unknown error'))
                    logger.error(f"Bitrix24 API error: {error_msg}")
                    raise Exception(f"Bitrix24 API error: {error_msg}")
                
                if return_full_response:
                    return data
                return data.get('result', {})
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"Request failed after {self.max_retries} attempts: {e}")
                    raise
        
        raise Exception("Failed to call Bitrix24 API")
    
    def get_list(self, method: str, params: Optional[Dict] = None, field_map: Optional[Dict] = None) -> List[Dict]:
        """
        Получение списка элементов с обработкой пагинации
        
        Args:
            method: Метод API для получения списка (например, 'crm.type.list')
            params: Дополнительные параметры запроса
            field_map: Маппинг полей из Bitrix24 в локальные (опционально)
            
        Returns:
            Список элементов
        """
        if params is None:
            params = {}
        
        all_items = []
        start = 0
        
        while True:
            params['start'] = start
            response = self._call_method(method, params)
            
            # Обработка разных форматов ответа
            if isinstance(response, list):
                items = response
            elif isinstance(response, dict):
                items = response.get('items', [])
                total = response.get('total', len(items))
            else:
                items = []
            
            if not items:
                break
            
            # Применяем маппинг полей, если указан
            if field_map:
                mapped_items = []
                for item in items:
                    mapped_item = {}
                    for bitrix_field, local_field in field_map.items():
                        if bitrix_field in item:
                            mapped_item[local_field] = item[bitrix_field]
                    # Сохраняем ID из Bitrix24
                    if 'ID' in item:
                        mapped_item['btxid'] = int(item['ID'])
                    mapped_items.append(mapped_item)
                all_items.extend(mapped_items)
            else:
                # Без маппинга просто добавляем ID в btxid
                for item in items:
                    if 'ID' in item and 'btxid' not in item:
                        item['btxid'] = int(item['ID'])
                all_items.extend(items)
            
            # Проверяем, есть ли еще данные
            if isinstance(response, dict):
                total = response.get('total', 0)
                if start + len(items) >= total:
                    break
            
            start += len(items)
            
            # Защита от бесконечного цикла
            if len(items) == 0:
                break
            
            # Небольшая задержка для соблюдения rate limiting
            time.sleep(0.1)
        
        return all_items
    
    def get_item(self, method: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Получение одного элемента
        
        Args:
            method: Метод API
            params: Параметры запроса
            
        Returns:
            Элемент или None
        """
        if params is None:
            params = {}
        
        response = self._call_method(method, params)
        
        if isinstance(response, dict):
            return response
        elif isinstance(response, list) and len(response) > 0:
            return response[0]
        
        return None

    def upload_file_to_disk(self, file_path: str) -> Optional[int]:
        """
        Загружает файл в диск Bitrix24 и возвращает ID загруженного файла (объекта диска).
        Использует disk.folder.uploadfile с base64-телом и Content-Type application/json; charset=windows-1251,
        как требуется для корректной загрузки фото в Bitrix24.

        Args:
            file_path: Полный путь к файлу на диске.

        Returns:
            ID объекта диска (FILE_ID) или None при ошибке.
        """
        path = Path(file_path)
        if not path.is_file():
            logger.warning(f"Файл не найден: {file_path}")
            return None
        try:
            with open(file_path, "rb") as f:
                encoded_bytes = base64.b64encode(f.read())
            encoded_string = str(encoded_bytes)[2:-1]  # убираем префикс b' и суффикс '
        except Exception as e:
            logger.error(f"Ошибка чтения/кодирования файла {file_path}: {e}")
            return None

        folder_id = getattr(Config, 'EXPORT_DISK_FOLDER_ID', '200931')
        # Имя файла: unixtime + оригинальное расширение (как в рабочем варианте b24_photo_send)
        unixtime_name = str(int(time.time()))
        ext = path.suffix if path.suffix else '.jpg'
        file_name = unixtime_name + ext

        method = 'disk.folder.uploadfile'
        request_url = f"{self.webhook_url}/{method}"
        payload = json.dumps({
            "id": folder_id,
            "data": {"NAME": file_name},
            "fileContent": encoded_string,
        }, ensure_ascii=False)

        try:
            response = requests.post(
                request_url,
                data=payload.encode('utf-8'),
                headers={'Content-Type': 'application/json; charset=windows-1251'},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            if data.get('error'):
                logger.error("Bitrix24 disk.folder.uploadfile error: %s", data.get('error_description', data.get('error')))
                return None
            result = data.get('result') or data
            if isinstance(result, dict):
                file_id = result.get('ID') or result.get('id')
                if file_id is not None:
                    return int(file_id)
            elif isinstance(result, int) and result > 0:
                return result
            logger.warning("Не удалось получить ID файла из ответа disk.folder.uploadfile: %s", data)
            return None
        except Exception as e:
            logger.error(f"Ошибка загрузки файла в Bitrix24: {e}", exc_info=True)
            return None
