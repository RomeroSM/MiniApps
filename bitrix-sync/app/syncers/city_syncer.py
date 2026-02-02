import logging
from typing import Dict, Any, List
from app.syncers.base_syncer import BaseSyncer
from app.database import get_models, get_session

logger = logging.getLogger(__name__)


class CitySyncer(BaseSyncer):
    """Синхронизатор справочника городов"""
    
    def get_bitrix_method(self) -> str:
        """Метод Bitrix24 API для получения городов"""
        return 'lists.field.get'
    
    def get_field_map(self) -> Dict[str, str]:
        """Маппинг полей Bitrix24 -> БД (не используется для городов)"""
        return {}
    
    def get_model_class(self):
        """Получить класс модели City"""
        models = get_models()
        return models['City']
    
    def create_or_update_item(self, bitrix_data: Dict, db_model_class) -> Any:
        """
        Создание или обновление города в БД
        
        Args:
            bitrix_data: Данные из Bitrix24 (с маппингом полей)
            db_model_class: Класс модели City
            
        Returns:
            Созданный или обновленный объект City
        """
        btxid = bitrix_data.get('btxid')
        if not btxid:
            logger.warning(f"Пропущен элемент без btxid: {bitrix_data}")
            return None
        
        # Ищем существующую запись по btxid
        existing = self.find_by_btxid(btxid, db_model_class)
        
        if existing:
            # Обновляем существующую запись
            if 'name' in bitrix_data:
                existing.name = bitrix_data['name']
            logger.debug(f"Обновлен город: {existing.name} (btxid={btxid})")
            return existing
        else:
            # Создаем новую запись
            city_data = {
                'name': bitrix_data.get('name', ''),
                'btxid': btxid
            }
            
            # Проверяем, нет ли города с таким именем (но без btxid)
            existing_by_name = self.session.query(db_model_class).filter_by(
                name=city_data['name']
            ).first()
            
            if existing_by_name:
                # Если нашли по имени, обновляем btxid
                existing_by_name.btxid = btxid
                logger.debug(f"Обновлен btxid для города: {existing_by_name.name}")
                return existing_by_name
            
            new_city = db_model_class(**city_data)
            self.session.add(new_city)
            logger.debug(f"Создан новый город: {new_city.name} (btxid={btxid})")
            return new_city
    
    def sync(self) -> Dict[str, Any]:
        """
        Переопределенный метод синхронизации для работы с lists.field.get
        Извлекает города из поля "Город" в IBLOCK_ID=77
        """
        logger.info(f"CitySyncer.sync() вызван - используется переопределенный метод")
        
        result = {
            'success': True,
            'created': 0,
            'updated': 0,
            'errors': []
        }
        
        try:
            self.session = get_session()
            
            # Получаем поля списка для IBLOCK_ID=77
            # Используем get_item, так как lists.field.get возвращает словарь полей
            method_name = self.get_bitrix_method()
            request_params = {
                'IBLOCK_TYPE_ID': 'bitrix_processes',
                'IBLOCK_ID': '77'  # Bitrix24 API ожидает строку
            }
            logger.info(f"Вызываем Bitrix24 метод: {method_name} с параметрами: {request_params}")
            
            response = self.bitrix_client.get_item(
                method=method_name,
                params=request_params
            )
            
            if not response or not isinstance(response, dict):
                raise Exception("Неверный формат ответа от Bitrix24")
            
            # Ищем поле с DISPLAY_VALUES_FORM и IBLOCK_ID=77
            # Обычно это PROPERTY_637 или другое поле типа PROPERTY_*
            city_field = None
            for field_key, field_data in response.items():
                if isinstance(field_data, dict):
                    # Проверяем, что это поле нужного списка (IBLOCK_ID=77) и есть DISPLAY_VALUES_FORM
                    if (field_data.get('IBLOCK_ID') == 77 and 
                        'DISPLAY_VALUES_FORM' in field_data and 
                        field_data.get('DISPLAY_VALUES_FORM')):
                        city_field = field_data
                        logger.info(f"Найдено поле с городами: {field_key} (IBLOCK_ID=77)")
                        break
            
            if not city_field:
                raise Exception("Поле с DISPLAY_VALUES_FORM и IBLOCK_ID=77 не найдено в ответе Bitrix24")
            
            # Извлекаем города из DISPLAY_VALUES_FORM
            display_values = city_field.get('DISPLAY_VALUES_FORM', {})
            if not display_values:
                logger.warning("DISPLAY_VALUES_FORM пуст или отсутствует")
                return result
            
            logger.info(f"Найдено {len(display_values)} городов в DISPLAY_VALUES_FORM")
            
            # Получаем класс модели
            model_class = self.get_model_class()
            
            # Синхронизируем каждый город
            for city_id_str, city_name in display_values.items():
                try:
                    city_id = int(city_id_str)
                    
                    # Проверяем, существует ли запись с таким btxid
                    existing = self.find_by_btxid(city_id, model_class)
                    
                    # Создаем или обновляем запись
                    city_data = {
                        'btxid': city_id,
                        'name': city_name
                    }
                    
                    if existing:
                        # Обновляем существующую запись
                        existing.name = city_name
                        logger.debug(f"Обновлен город: {city_name} (btxid={city_id})")
                        result['updated'] += 1
                    else:
                        # Проверяем, нет ли города с таким именем (но без btxid)
                        existing_by_name = self.session.query(model_class).filter_by(
                            name=city_name
                        ).first()
                        
                        if existing_by_name:
                            # Если нашли по имени, обновляем btxid
                            existing_by_name.btxid = city_id
                            logger.debug(f"Обновлен btxid для города: {city_name}")
                            result['updated'] += 1
                        else:
                            # Создаем новую запись
                            new_city = model_class(**city_data)
                            self.session.add(new_city)
                            logger.debug(f"Создан новый город: {city_name} (btxid={city_id})")
                            result['created'] += 1
                            
                except ValueError:
                    error_msg = f"Неверный формат ID города: {city_id_str}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
                except Exception as e:
                    error_msg = f"Ошибка при синхронизации города {city_name} (ID: {city_id_str}): {e}"
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