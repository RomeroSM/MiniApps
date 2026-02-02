import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from app.bitrix_client import Bitrix24Client
from app.database import get_session

logger = logging.getLogger(__name__)


class BaseSyncer(ABC):
    """Базовый класс для синхронизаторов справочников"""
    
    def __init__(self, bitrix_client: Bitrix24Client):
        """
        Инициализация синхронизатора
        
        Args:
            bitrix_client: Клиент для работы с Bitrix24 API
        """
        self.bitrix_client = bitrix_client
        self.session = None
    
    @abstractmethod
    def get_bitrix_method(self) -> str:
        """
        Возвращает название метода Bitrix24 API для получения данных
        
        Returns:
            Название метода API
        """
        pass
    
    @abstractmethod
    def get_field_map(self) -> Dict[str, str]:
        """
        Возвращает маппинг полей Bitrix24 -> поля БД
        
        Returns:
            Словарь {bitrix_field: db_field}
        """
        pass
    
    @abstractmethod
    def get_model_class(self):
        """
        Возвращает класс модели SQLAlchemy для данного справочника
        
        Returns:
            Класс модели
        """
        pass
    
    @abstractmethod
    def create_or_update_item(self, bitrix_data: Dict, db_model_class) -> Any:
        """
        Создание или обновление записи в БД
        
        Args:
            bitrix_data: Данные из Bitrix24 (уже с маппингом полей)
            db_model_class: Класс модели БД
            
        Returns:
            Созданный или обновленный объект модели
        """
        pass
    
    def sync(self) -> Dict[str, Any]:
        """
        Основной метод синхронизации справочника
        
        Returns:
            Словарь с результатами синхронизации:
            {
                'success': bool,
                'created': int,
                'updated': int,
                'errors': List[str]
            }
        """
        result = {
            'success': True,
            'created': 0,
            'updated': 0,
            'errors': []
        }
        
        try:
            self.session = get_session()
            
            # Получаем данные из Bitrix24
            field_map = self.get_field_map()
            field_map['ID'] = 'btxid'  # Всегда добавляем маппинг ID -> btxid
            
            bitrix_items = self.bitrix_client.get_list(
                method=self.get_bitrix_method(),
                field_map=field_map
            )
            
            logger.info(f"Получено {len(bitrix_items)} элементов из Bitrix24 для {self.__class__.__name__}")
            
            # Получаем класс модели
            model_class = self.get_model_class()
            
            # Синхронизируем каждый элемент
            for bitrix_item in bitrix_items:
                try:
                    btxid = bitrix_item.get('btxid')
                    
                    # Проверяем, существует ли запись с таким btxid
                    existing = None
                    if btxid:
                        existing = self.find_by_btxid(btxid, model_class)
                    
                    # Создаем или обновляем запись
                    item = self.create_or_update_item(bitrix_item, model_class)
                    
                    if item:
                        # Определяем, была ли это новая запись или обновление
                        if existing:
                            # Запись уже существовала - это обновление
                            result['updated'] += 1
                        else:
                            # Записи не было - это создание
                            result['created'] += 1
                except Exception as e:
                    error_msg = f"Ошибка при синхронизации элемента {bitrix_item}: {e}"
                    logger.error(error_msg, exc_info=True)
                    result['errors'].append(error_msg)
            
            # Коммитим изменения
            self.session.commit()
            logger.info(f"Синхронизация {self.__class__.__name__} завершена: создано {result['created']}, обновлено {result['updated']}")
            
        except Exception as e:
            logger.error(f"Ошибка при синхронизации {self.__class__.__name__}: {e}", exc_info=True)
            result['success'] = False
            result['errors'].append(str(e))
            if self.session:
                self.session.rollback()
        finally:
            if self.session:
                self.session.close()
        
        return result
    
    def find_by_btxid(self, btxid: int, model_class) -> Optional[Any]:
        """
        Поиск записи по btxid
        
        Args:
            btxid: ID в Bitrix24
            model_class: Класс модели БД
            
        Returns:
            Найденный объект или None
        """
        if not self.session:
            self.session = get_session()
        
        return self.session.query(model_class).filter_by(btxid=btxid).first()
