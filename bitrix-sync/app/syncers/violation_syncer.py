import logging
from typing import Dict, Any
from app.syncers.base_syncer import BaseSyncer
from app.database import get_models, get_session

logger = logging.getLogger(__name__)

# IBLOCK_ID списка нарушений в Bitrix24
VIOLATION_IBLOCK_ID = 123


class ViolationSyncer(BaseSyncer):
    """Синхронизатор справочника нарушений"""

    def get_bitrix_method(self) -> str:
        """Метод Bitrix24 API для получения нарушений"""
        return 'lists.element.get'

    def get_field_map(self) -> Dict[str, str]:
        """Маппинг полей Bitrix24 -> БД (не используется при переопределённом sync)"""
        return {'NAME': 'name', 'CATEGORY_BTXID': 'category_btxid'}

    def get_model_class(self):
        """Получить класс модели Violation"""
        models = get_models()
        return models['Violation']

    def create_or_update_item(self, bitrix_data: Dict, db_model_class) -> Any:
        """Создание или обновление нарушения в БД (используется базовой логикой при необходимости)."""
        btxid = bitrix_data.get('btxid')
        if not btxid:
            logger.warning(f"Пропущен элемент без btxid: {bitrix_data}")
            return None
        models = get_models()
        ViolationCategory = models['ViolationCategory']
        category_btxid = bitrix_data.get('category_btxid')
        if not category_btxid:
            logger.warning(f"Нарушение {bitrix_data.get('name')} без category_btxid, пропускаем")
            return None
        category = self.session.query(ViolationCategory).filter_by(btxid=category_btxid).first()
        if not category:
            logger.warning(f"Категория с btxid={category_btxid} не найдена, пропускаем нарушение {bitrix_data.get('name')}")
            return None
        existing = self.find_by_btxid(btxid, db_model_class)
        if existing:
            if 'name' in bitrix_data:
                existing.name = bitrix_data['name']
            if category.id != existing.category_id:
                existing.category_id = category.id
            logger.debug(f"Обновлено нарушение: {existing.name} (btxid={btxid})")
            return existing
        violation_data = {
            'name': bitrix_data.get('name', ''),
            'category_id': category.id,
            'btxid': btxid
        }
        new_violation = db_model_class(**violation_data)
        self.session.add(new_violation)
        logger.debug(f"Создано новое нарушение: {new_violation.name} (btxid={btxid}, category_id={category.id})")
        return new_violation

    def sync(self) -> Dict[str, Any]:
        """
        Синхронизация нарушений через lists.element.get.
        IBLOCK_ID=123, один вызов; из элементов: ID, NAME, PROPERTY_1091 (категория).
        """
        logger.info("ViolationSyncer.sync() — переопределённый метод (lists.element.get, IBLOCK_ID=123)")
        result = {'success': True, 'created': 0, 'updated': 0, 'errors': []}
        try:
            self.session = get_session()
            from app.database import ensure_violations_state_column
            ensure_violations_state_column()

            method_name = self.get_bitrix_method()
            request_params = {
                'IBLOCK_TYPE_ID': 'bitrix_processes',
                'IBLOCK_ID': str(VIOLATION_IBLOCK_ID),
            }
            logger.info(f"Вызываем Bitrix24: {method_name} с параметрами: {request_params}")
            response = self.bitrix_client._call_method(method_name, request_params)
            if isinstance(response, list):
                all_elements = response
            elif isinstance(response, dict):
                all_elements = response.get('items', [])
            else:
                all_elements = []
            logger.info(f"Получено {len(all_elements)} элементов из Bitrix24")
            if not all_elements:
                logger.warning("Не получено элементов из Bitrix24")
                return result

            # Расшифровка состояния: lists.field.get (IBLOCK_ID=123) → PROPERTY_1115 → DISPLAY_VALUES_FORM
            state_display_values = {}
            try:
                field_response = self.bitrix_client.get_item(
                    'lists.field.get',
                    {'IBLOCK_TYPE_ID': 'bitrix_processes', 'IBLOCK_ID': str(VIOLATION_IBLOCK_ID)}
                )
                if isinstance(field_response, dict):
                    prop1115 = field_response.get('PROPERTY_1115')
                    if isinstance(prop1115, dict) and prop1115.get('DISPLAY_VALUES_FORM'):
                        state_display_values = prop1115.get('DISPLAY_VALUES_FORM') or {}
                if state_display_values:
                    logger.info(f"Загружено {len(state_display_values)} значений состояния (PROPERTY_1115)")
            except Exception as e:
                logger.warning(f"Не удалось загрузить расшифровку PROPERTY_1115: {e}")

            model_class = self.get_model_class()
            models = get_models()
            ViolationCategory = models['ViolationCategory']
            for element in all_elements:
                try:
                    element_id = element.get('ID')
                    if not element_id:
                        logger.warning(f"Элемент без ID пропущен: {element}")
                        continue
                    try:
                        element_btxid = int(element_id)
                    except (ValueError, TypeError):
                        logger.warning(f"Неверный формат ID элемента: {element_id}")
                        continue
                    violation_name = element.get('NAME', '').strip()
                    if not violation_name:
                        logger.warning(f"Элемент {element_btxid} без NAME, пропускаем")
                        continue
                    # PROPERTY_1091 — btxid категории (список, строка/число или словарь)
                    property_1091 = element.get('PROPERTY_1091')
                    category_btxid = None
                    if property_1091 is not None:
                        if isinstance(property_1091, list) and len(property_1091) > 0:
                            category_btxid = property_1091[0]
                        elif isinstance(property_1091, dict) and property_1091:
                            category_btxid = next(iter(property_1091.values()), None)
                        elif isinstance(property_1091, (str, int)):
                            category_btxid = property_1091
                        try:
                            category_btxid = int(category_btxid) if category_btxid else None
                        except (ValueError, TypeError):
                            category_btxid = None
                    if not category_btxid:
                        logger.warning(f"Нарушение {violation_name} (ID: {element_btxid}) без PROPERTY_1091, пропускаем")
                        continue

                    # PROPERTY_1115 — код состояния (словарь/список/строка), расшифровка из state_display_values
                    property_1115 = element.get('PROPERTY_1115')
                    state_code = None
                    if property_1115 is not None:
                        if isinstance(property_1115, list) and len(property_1115) > 0:
                            state_code = property_1115[0]
                        elif isinstance(property_1115, dict) and property_1115:
                            state_code = next(iter(property_1115.values()), None)
                        elif isinstance(property_1115, (str, int)):
                            state_code = property_1115
                        if state_code is not None:
                            try:
                                state_code = str(int(state_code)) if state_code else None
                            except (ValueError, TypeError):
                                state_code = str(state_code) if state_code else None
                    state_label = None
                    if state_code is not None:
                        state_label = state_display_values.get(str(state_code)) or state_display_values.get(state_code)

                    category = self.session.query(ViolationCategory).filter_by(btxid=category_btxid).first()
                    if not category:
                        logger.warning(f"Категория с btxid={category_btxid} не найдена, пропускаем нарушение {violation_name} (ID: {element_btxid})")
                        continue
                    existing = self.find_by_btxid(element_btxid, model_class)
                    if existing:
                        existing.name = violation_name
                        if category.id != existing.category_id:
                            existing.category_id = category.id
                        existing.state = state_label
                        logger.debug(f"Обновлено нарушение: {violation_name} (btxid={element_btxid})")
                        result['updated'] += 1
                    else:
                        existing_by_name = self.session.query(model_class).filter_by(
                            name=violation_name,
                            category_id=category.id
                        ).first()
                        if existing_by_name:
                            existing_by_name.btxid = element_btxid
                            existing_by_name.state = state_label
                            logger.debug(f"Обновлен btxid для нарушения: {violation_name}")
                            result['updated'] += 1
                        else:
                            new_violation = model_class(
                                name=violation_name,
                                category_id=category.id,
                                btxid=element_btxid,
                                state=state_label
                            )
                            self.session.add(new_violation)
                            logger.debug(f"Создано нарушение: {violation_name} (btxid={element_btxid}, category_id={category.id})")
                            result['created'] += 1
                except Exception as e:
                    error_msg = f"Ошибка при синхронизации нарушения {element.get('NAME', 'Unknown')} (ID: {element.get('ID', 'Unknown')}): {e}"
                    logger.error(error_msg, exc_info=True)
                    result['errors'].append(error_msg)
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
