import logging
from typing import Dict, Any
from app.syncers.base_syncer import BaseSyncer
from app.database import get_models, get_session

logger = logging.getLogger(__name__)

# IBLOCK_ID списка категорий нарушений в Bitrix24
VIOLATION_IBLOCK_ID = 127


class ViolationCategorySyncer(BaseSyncer):
    """Синхронизатор справочника категорий нарушений"""

    def get_bitrix_method(self) -> str:
        """Метод Bitrix24 API для получения категорий нарушений"""
        return 'lists.element.get'

    def get_field_map(self) -> Dict[str, str]:
        """Маппинг полей Bitrix24 -> БД (не используется при переопределённом sync)"""
        return {'NAME': 'name'}

    def get_model_class(self):
        """Получить класс модели ViolationCategory"""
        models = get_models()
        return models['ViolationCategory']

    def create_or_update_item(self, bitrix_data: Dict, db_model_class) -> Any:
        """Создание или обновление категории в БД (используется базовой логикой при необходимости)."""
        btxid = bitrix_data.get('btxid')
        if not btxid:
            logger.warning(f"Пропущен элемент без btxid: {bitrix_data}")
            return None
        existing = self.find_by_btxid(btxid, db_model_class)
        if existing:
            if 'name' in bitrix_data:
                existing.name = bitrix_data['name']
            logger.debug(f"Обновлена категория: {existing.name} (btxid={btxid})")
            return existing
        category_data = {'name': bitrix_data.get('name', ''), 'btxid': btxid}
        existing_by_name = self.session.query(db_model_class).filter_by(name=category_data['name']).first()
        if existing_by_name:
            existing_by_name.btxid = btxid
            logger.debug(f"Обновлен btxid для категории: {existing_by_name.name}")
            return existing_by_name
        new_category = db_model_class(**category_data)
        self.session.add(new_category)
        logger.debug(f"Создана новая категория: {new_category.name} (btxid={btxid})")
        return new_category

    def sync(self) -> Dict[str, Any]:
        """
        Синхронизация категорий нарушений через lists.element.get.
        IBLOCK_ID=127; btxid из поля ID, name из поля NAME элемента списка.
        """
        logger.info("ViolationCategorySyncer.sync() — переопределённый метод (lists.element.get, IBLOCK_ID=127)")
        result = {'success': True, 'created': 0, 'updated': 0, 'errors': []}
        try:
            self.session = get_session()
            request_params = {
                'IBLOCK_TYPE_ID': 'bitrix_processes',
                'IBLOCK_ID': str(VIOLATION_IBLOCK_ID),
            }
            logger.info(f"Вызываем Bitrix24: lists.element.get с параметрами: {request_params}")
            response = self.bitrix_client._call_method('lists.element.get', request_params)
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
            model_class = self.get_model_class()
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
                    cat_name = element.get('NAME', '').strip()
                    existing = self.find_by_btxid(element_btxid, model_class)
                    if existing:
                        existing.name = cat_name
                        logger.debug(f"Обновлена категория: {cat_name} (btxid={element_btxid})")
                        result['updated'] += 1
                    else:
                        existing_by_name = self.session.query(model_class).filter_by(name=cat_name).first()
                        if existing_by_name:
                            existing_by_name.btxid = element_btxid
                            logger.debug(f"Обновлен btxid для категории: {cat_name}")
                            result['updated'] += 1
                        else:
                            new_cat = model_class(name=cat_name, btxid=element_btxid)
                            self.session.add(new_cat)
                            logger.debug(f"Создана категория: {cat_name} (btxid={element_btxid})")
                            result['created'] += 1
                except Exception as e:
                    error_msg = f"Ошибка при синхронизации категории {element.get('NAME', 'Unknown')} (ID: {element.get('ID', 'Unknown')}): {e}"
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
