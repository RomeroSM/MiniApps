"""
Экспорт заявок из form_submissions в список Bitrix24 (IBLOCK_ID=125).
После успешной выгрузки записи удаляются из БД.
"""
import logging
from typing import Dict, Any, Optional
from app.bitrix_client import Bitrix24Client
from app.database import get_session, get_models
from app.config import Config

logger = logging.getLogger(__name__)


def run_export(bitrix_client: Optional[Bitrix24Client] = None) -> Dict[str, Any]:
    """
    Выгружает все записи из form_submissions в Bitrix24 (lists.element.add, IBLOCK_ID=125).
    При успешном ответе от Bitrix запись удаляется из БД.

    Returns:
        {'success': bool, 'exported': int, 'deleted': int, 'errors': list}
    """
    result = {'success': True, 'exported': 0, 'deleted': 0, 'errors': []}
    client = bitrix_client or Bitrix24Client()
    session = get_session()
    try:
        models = get_models()
        FormSubmission = models['FormSubmission']
        City = models['City']
        Object = models['Object']
        ViolationCategory = models['ViolationCategory']
        Violation = models['Violation']

        rows = session.query(FormSubmission).order_by(FormSubmission.id).all()
        if not rows:
            logger.debug("Нет заявок для экспорта")
            return result

        for sub in rows:
            try:
                city = session.query(City).filter_by(btxid=sub.city_id).first()
                obj = session.query(Object).filter_by(btxid=sub.object_id).first()
                cat = session.query(ViolationCategory).filter_by(btxid=sub.violation_category_id).first()
                viol = session.query(Violation).filter_by(btxid=sub.violation_id).first()
                # NAME — короткий заголовок для списка (город, объект, нарушение), не из comment
                name_parts = [f"Заявка #{sub.id}"]
                if city:
                    name_parts.append(city.name)
                if obj:
                    name_parts.append(obj.name)
                if viol:
                    name_parts.append(viol.name)
                name = ": ".join(name_parts)[:500]
                fields = {'NAME': name}
                if Config.EXPORT_PROPERTY_CITY and city and city.btxid is not None:
                    fields[Config.EXPORT_PROPERTY_CITY] = str(city.btxid)
                if Config.EXPORT_PROPERTY_OBJECT and obj and obj.btxid is not None:
                    fields[Config.EXPORT_PROPERTY_OBJECT] = str(obj.btxid)
                if Config.EXPORT_PROPERTY_CATEGORY and cat and cat.btxid is not None:
                    fields[Config.EXPORT_PROPERTY_CATEGORY] = str(cat.btxid)
                if Config.EXPORT_PROPERTY_VIOLATION and viol and viol.btxid is not None:
                    fields[Config.EXPORT_PROPERTY_VIOLATION] = str(viol.btxid)
                if Config.EXPORT_PROPERTY_COMMENT:
                    fields[Config.EXPORT_PROPERTY_COMMENT] = (sub.comment or '')[:500]
                if Config.EXPORT_PROPERTY_FILE and sub.file_path:
                    fields[Config.EXPORT_PROPERTY_FILE] = (sub.file_path or '')[:500]
                if Config.EXPORT_PROPERTY_TELEGRAM_USER_ID and sub.telegram_user_id is not None:
                    fields[Config.EXPORT_PROPERTY_TELEGRAM_USER_ID] = str(sub.telegram_user_id)

                params = {
                    'IBLOCK_TYPE_ID': Config.EXPORT_IBLOCK_TYPE_ID,
                    'IBLOCK_ID': Config.EXPORT_IBLOCK_ID,
                    'ELEMENT_CODE': f'sub_{sub.id}',
                    'FIELDS': fields,
                }
                api_result = client._call_method('lists.element.add', params)

                success = False
                if api_result is not None:
                    if isinstance(api_result, int) and api_result > 0:
                        success = True
                    elif isinstance(api_result, dict) and (api_result.get('ID') or api_result.get('id')):
                        success = True

                if success:
                    session.delete(sub)
                    result['deleted'] += 1
                    result['exported'] += 1
                    logger.info(f"Заявка #{sub.id} выгружена в Bitrix, удалена из БД")
                else:
                    result['errors'].append(f"Заявка #{sub.id}: Bitrix вернул неожиданный результат: {api_result}")
                    logger.warning(f"Заявка #{sub.id}: не удалось считать успех из ответа Bitrix: {api_result}")

            except Exception as e:
                result['success'] = False
                result['errors'].append(f"Заявка #{sub.id}: {e}")
                logger.error(f"Ошибка экспорта заявки #{sub.id}: {e}", exc_info=True)

        session.commit()
        logger.info(f"Экспорт заявок завершён: выгружено {result['exported']}, удалено {result['deleted']}, ошибок {len(result['errors'])}")
    except Exception as e:
        logger.error(f"Ошибка при экспорте заявок: {e}", exc_info=True)
        result['success'] = False
        result['errors'].append(str(e))
        session.rollback()
    finally:
        session.close()
    return result
