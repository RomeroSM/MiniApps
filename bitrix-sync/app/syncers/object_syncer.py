import logging
import time
from typing import Dict, Any, Optional, List
from app.syncers.base_syncer import BaseSyncer
from app.database import get_models, get_session

logger = logging.getLogger(__name__)


class ObjectSyncer(BaseSyncer):
    """Синхронизатор справочника объектов"""
    
    def get_bitrix_method(self) -> str:
        """Метод Bitrix24 API для получения объектов"""
        return 'lists.element.get'
    
    def get_field_map(self) -> Dict[str, str]:
        """Маппинг полей Bitrix24 -> БД (не используется для объектов)"""
        return {}
    
    def get_model_class(self):
        """Получить класс модели Object"""
        models = get_models()
        return models['Object']
    
    def create_or_update_item(self, bitrix_data: Dict, db_model_class) -> Any:
        """
        Создание или обновление объекта в БД
        
        Args:
            bitrix_data: Данные из Bitrix24 (с маппингом полей)
            db_model_class: Класс модели Object
            
        Returns:
            Созданный или обновленный объект Object
        """
        btxid = bitrix_data.get('btxid')
        if not btxid:
            logger.warning(f"Пропущен элемент без btxid: {bitrix_data}")
            return None
        
        models = get_models()
        City = models['City']
        
        # Находим город по btxid из Bitrix24
        city_btxid = bitrix_data.get('city_btxid')
        if not city_btxid:
            logger.warning(f"Объект {bitrix_data.get('name')} без city_btxid, пропускаем")
            return None
        
        city = self.session.query(City).filter_by(btxid=city_btxid).first()
        if not city:
            logger.warning(f"Город с btxid={city_btxid} не найден, пропускаем объект {bitrix_data.get('name')}")
            return None
        
        # Ищем существующую запись по btxid
        existing = self.find_by_btxid(btxid, db_model_class)
        
        if existing:
            # Обновляем существующую запись
            if 'name' in bitrix_data:
                existing.name = bitrix_data['name']
            if city.id != existing.city_id:
                existing.city_id = city.id
            logger.debug(f"Обновлен объект: {existing.name} (btxid={btxid})")
            return existing
        else:
            # Создаем новую запись
            object_data = {
                'name': bitrix_data.get('name', ''),
                'city_id': city.id,
                'btxid': btxid
            }
            
            new_object = db_model_class(**object_data)
            self.session.add(new_object)
            logger.debug(f"Создан новый объект: {new_object.name} (btxid={btxid}, city_id={city.id})")
            return new_object
    
    def sync(self) -> Dict[str, Any]:
        """
        Переопределенный метод синхронизации для работы с lists.element.get
        Получает элементы списка и извлекает объекты с их связью с городами через PROPERTY_637
        """
        logger.info(f"ObjectSyncer.sync() вызван - используется переопределенный метод")
        
        result = {
            'success': True,
            'created': 0,
            'updated': 0,
            'errors': []
        }
        
        try:
            self.session = get_session()
            # Убеждаемся, что колонка state есть в таблице objects (bitrix-sync не вызывает init_db веб-приложения)
            from app.database import ensure_objects_state_column
            ensure_objects_state_column()

            # Получаем элементы списка для IBLOCK_ID=77 с пагинацией по start/next
            method_name = self.get_bitrix_method()
            request_params = {
                'IBLOCK_TYPE_ID': 'bitrix_processes',
                'IBLOCK_ID': '77',
                'start': 0,
            }
            all_elements = []
            while True:
                logger.info(f"Вызываем Bitrix24 метод: {method_name} с параметрами: {request_params}")
                full_response = self.bitrix_client._call_method(method_name, request_params, return_full_response=True)
                api_result = full_response.get('result') if isinstance(full_response, dict) else full_response
                next_start = full_response.get('next') if isinstance(full_response, dict) else None

                if isinstance(api_result, list):
                    chunk = api_result
                elif isinstance(api_result, dict):
                    chunk = api_result.get('items', [])
                else:
                    chunk = []
                all_elements.extend(chunk)

                if next_start is None:
                    break
                request_params['start'] = next_start
                time.sleep(0.1)

            logger.info(f"Получено {len(all_elements)} элементов из Bitrix24")
            
            if not all_elements:
                logger.warning("Не получено элементов из Bitrix24")
                return result  # result — словарь с created/updated/errors
            
            # Расшифровка состояния: lists.field.get (IBLOCK_ID=77) → PROPERTY_645 → DISPLAY_VALUES_FORM (id → label)
            state_display_values = {}
            try:
                field_response = self.bitrix_client.get_item(
                    'lists.field.get',
                    {'IBLOCK_TYPE_ID': 'bitrix_processes', 'IBLOCK_ID': '77'}
                )
                if isinstance(field_response, dict):
                    prop645 = field_response.get('PROPERTY_645')
                    if isinstance(prop645, dict) and prop645.get('DISPLAY_VALUES_FORM'):
                        state_display_values = prop645.get('DISPLAY_VALUES_FORM') or {}
                if state_display_values:
                    logger.info(f"Загружено {len(state_display_values)} значений состояния (PROPERTY_645)")
            except Exception as e:
                logger.warning(f"Не удалось загрузить расшифровку PROPERTY_645: {e}")
            
            # Получаем классы моделей
            model_class = self.get_model_class()
            models = get_models()
            City = models['City']
            
            # Синхронизируем каждый объект
            for element in all_elements:
                try:
                    # Извлекаем ID элемента (btxid)
                    element_id = element.get('ID')
                    if not element_id:
                        logger.warning(f"Элемент без ID пропущен: {element}")
                        continue
                    
                    try:
                        element_btxid = int(element_id)
                    except (ValueError, TypeError):
                        logger.warning(f"Неверный формат ID элемента: {element_id}")
                        continue
                    
                    # Извлекаем название объекта из поля NAME
                    object_name = element.get('NAME', '').strip()
                    if not object_name:
                        logger.warning(f"Элемент {element_btxid} без NAME, пропускаем")
                        continue
                    
                    # Извлекаем ID города из PROPERTY_637
                    # Bitrix может вернуть: список, строку/число или словарь вида {'99973': '1469'}
                    property_637 = element.get('PROPERTY_637')
                    city_btxid = None
                    
                    if property_637 is not None:
                        if isinstance(property_637, list) and len(property_637) > 0:
                            city_btxid = property_637[0]
                        elif isinstance(property_637, dict) and property_637:
                            # словарь вида {'internal_id': 'btxid_города'}
                            city_btxid = next(iter(property_637.values()), None)
                        elif isinstance(property_637, (str, int)):
                            city_btxid = property_637
                        
                        try:
                            city_btxid = int(city_btxid) if city_btxid else None
                        except (ValueError, TypeError):
                            city_btxid = None
                    
                    if not city_btxid:
                        logger.warning(f"Объект {object_name} (ID: {element_btxid}) без PROPERTY_637, пропускаем")
                        continue
                    
                    # Извлекаем код состояния из PROPERTY_645 (словарь/список/строка — как PROPERTY_637)
                    property_645 = element.get('PROPERTY_645')
                    state_code = None
                    if property_645 is not None:
                        if isinstance(property_645, list) and len(property_645) > 0:
                            state_code = property_645[0]
                        elif isinstance(property_645, dict) and property_645:
                            state_code = next(iter(property_645.values()), None)
                        elif isinstance(property_645, (str, int)):
                            state_code = property_645
                        if state_code is not None:
                            try:
                                state_code = str(int(state_code)) if state_code else None
                            except (ValueError, TypeError):
                                state_code = str(state_code) if state_code else None
                    state_label = None
                    if state_code is not None:
                        state_label = state_display_values.get(str(state_code)) or state_display_values.get(state_code)
                    
                    # Находим город по btxid
                    city = self.session.query(City).filter_by(btxid=city_btxid).first()
                    if not city:
                        logger.warning(f"Город с btxid={city_btxid} не найден, пропускаем объект {object_name} (ID: {element_btxid})")
                        continue
                    
                    # Проверяем, существует ли запись с таким btxid
                    existing = self.find_by_btxid(element_btxid, model_class)
                    
                    if existing:
                        # Обновляем существующую запись
                        existing.name = object_name
                        if city.id != existing.city_id:
                            existing.city_id = city.id
                        existing.state = state_label
                        logger.debug(f"Обновлен объект: {object_name} (btxid={element_btxid}, city_id={city.id})")
                        result['updated'] += 1
                    else:
                        # Проверяем, нет ли объекта с таким именем (но без btxid)
                        existing_by_name = self.session.query(model_class).filter_by(
                            name=object_name,
                            city_id=city.id
                        ).first()
                        
                        if existing_by_name:
                            # Если нашли по имени и городу, обновляем btxid и state
                            existing_by_name.btxid = element_btxid
                            existing_by_name.state = state_label
                            logger.debug(f"Обновлен btxid для объекта: {object_name}")
                            result['updated'] += 1
                        else:
                            # Создаем новую запись
                            object_data = {
                                'name': object_name,
                                'city_id': city.id,
                                'btxid': element_btxid,
                                'state': state_label
                            }
                            
                            new_object = model_class(**object_data)
                            self.session.add(new_object)
                            logger.debug(f"Создан новый объект: {object_name} (btxid={element_btxid}, city_id={city.id})")
                            result['created'] += 1
                            
                except Exception as e:
                    error_msg = f"Ошибка при синхронизации объекта {element.get('NAME', 'Unknown')} (ID: {element.get('ID', 'Unknown')}): {e}"
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