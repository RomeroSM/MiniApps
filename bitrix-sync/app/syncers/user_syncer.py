import logging
from typing import Dict, Any
from app.syncers.base_syncer import BaseSyncer
from app.database import get_models

logger = logging.getLogger(__name__)


class UserSyncer(BaseSyncer):
    """Синхронизатор справочника пользователей"""
    
    def get_bitrix_method(self) -> str:
        """Метод Bitrix24 API для получения пользователей"""
        # В Bitrix24 используется метод user.get или user.get.list
        return 'user.get'  # Замените на правильный метод если нужно
    
    def get_field_map(self) -> Dict[str, str]:
        """Маппинг полей Bitrix24 -> БД"""
        return {
            'NAME': 'first_name',  # Имя
            'LAST_NAME': 'last_name',  # Фамилия
            # ВАЖНО: tg_id и secret_key обычно не синхронизируются из Bitrix24
            # Они заполняются локально в основной системе
        }
    
    def get_model_class(self):
        """Получить класс модели User"""
        models = get_models()
        return models['User']
    
    def create_or_update_item(self, bitrix_data: Dict, db_model_class) -> Any:
        """
        Создание или обновление пользователя в БД
        
        Args:
            bitrix_data: Данные из Bitrix24 (с маппингом полей)
            db_model_class: Класс модели User
            
        Returns:
            Созданный или обновленный объект User или None если tg_id обязателен
        """
        btxid = bitrix_data.get('btxid')
        if not btxid:
            logger.warning(f"Пропущен элемент без btxid: {bitrix_data}")
            return None
        
        # Ищем существующую запись по btxid
        existing = self.find_by_btxid(btxid, db_model_class)
        
        if existing:
            # Обновляем существующую запись (но не трогаем tg_id и secret_key)
            if 'first_name' in bitrix_data:
                existing.first_name = bitrix_data['first_name']
            if 'last_name' in bitrix_data:
                existing.last_name = bitrix_data['last_name']
            logger.debug(f"Обновлен пользователь: {existing.first_name} {existing.last_name} (btxid={btxid})")
            return existing
        else:
            # Для новых пользователей требуются tg_id и secret_key
            # Если их нет, мы не можем создать пользователя без них
            # В этом случае просто обновляем btxid у существующего пользователя с таким именем
            first_name = bitrix_data.get('first_name', '')
            last_name = bitrix_data.get('last_name', '')
            
            # Ищем пользователя по имени и фамилии
            existing_by_name = self.session.query(db_model_class).filter_by(
                first_name=first_name,
                last_name=last_name
            ).first()
            
            if existing_by_name:
                # Если нашли по имени, обновляем btxid
                existing_by_name.btxid = btxid
                logger.debug(f"Обновлен btxid для пользователя: {existing_by_name.first_name} {existing_by_name.last_name}")
                return existing_by_name
            else:
                # Не можем создать пользователя без tg_id и secret_key
                # Это должно быть сделано в основной системе
                logger.warning(f"Не удалось создать пользователя {first_name} {last_name}: требуется tg_id и secret_key")
                return None
