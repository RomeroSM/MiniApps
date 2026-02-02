import logging
from typing import List, Dict, Any, Optional
from app.bitrix_client import Bitrix24Client
from app.syncers.city_syncer import CitySyncer
from app.syncers.object_syncer import ObjectSyncer
from app.syncers.category_syncer import ViolationCategorySyncer
from app.syncers.violation_syncer import ViolationSyncer
from app.syncers.user_syncer import UserSyncer
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class SyncEngine:
    """Движок синхронизации справочников с Bitrix24"""
    
    # Доступные синхронизаторы
    SYNCERS = {
        'city': CitySyncer,
        'cities': CitySyncer,
        'object': ObjectSyncer,
        'objects': ObjectSyncer,
        'category': ViolationCategorySyncer,
        'categories': ViolationCategorySyncer,
        'violation_category': ViolationCategorySyncer,
        'violation_categories': ViolationCategorySyncer,
        'violation': ViolationSyncer,
        'violations': ViolationSyncer,
        'user': UserSyncer,
        'users': UserSyncer,
    }
    
    def __init__(self, bitrix_client: Optional[Bitrix24Client] = None):
        """
        Инициализация движка синхронизации
        
        Args:
            bitrix_client: Клиент Bitrix24. Если не указан, создается новый
        """
        self.bitrix_client = bitrix_client or Bitrix24Client()
    
    def sync_all(self) -> Dict[str, Any]:
        """
        Синхронизация всех справочников
        
        Returns:
            Словарь с результатами синхронизации для каждого справочника
        """
        logger.info("Начало синхронизации всех справочников")
        
        results = {
            'success': True,
            'syncers': {},
            'summary': {
                'total_created': 0,
                'total_updated': 0,
                'total_errors': 0
            }
        }
        
        # Порядок синхронизации — зависимость: city -> object.
        # Остальные синкеры могут запускаться параллельно.
        sync_order = [
            ('city', 'Города'),
            ('category', 'Категории нарушений'),
            ('object', 'Объекты'),
            ('violation', 'Нарушения'),
            ('user', 'Пользователи'),
        ]

        def _run_syncer(syncer_key: str) -> Dict[str, Any]:
            """Вспомогательная обёртка для запуска одного синкера и возврата результата."""
            try:
                syncer_class = self.SYNCERS[syncer_key]
                logger.info(f"Синхронизация справочника: {syncer_key}")
                syncer = syncer_class(self.bitrix_client)
                result = syncer.sync()
                return result
            except Exception as e:
                logger.error(f"Ошибка при синхронизации {syncer_key}: {e}", exc_info=True)
                return {
                    'success': False,
                    'created': 0,
                    'updated': 0,
                    'errors': [str(e)]
                }

        # План параллельного запуска:
        # 1) city и category — запускаем первыми
        # 2) user — параллельно
        # 3) object — после city; violation — после category
        executor = ThreadPoolExecutor(max_workers=4)
        futures = {}
        try:
            futures['city'] = executor.submit(_run_syncer, 'city')
            futures['category'] = executor.submit(_run_syncer, 'category')
            futures['user'] = executor.submit(_run_syncer, 'user')

            def _run_object_after_city():
                try:
                    city_result = futures['city'].result()
                    if not city_result.get('success', True):
                        return {
                            'success': False,
                            'created': 0,
                            'updated': 0,
                            'errors': [f"Dependency failed: city sync failed, object sync skipped"]
                        }
                except Exception as e:
                    logger.error(f"City sync failed, skipping object sync: {e}", exc_info=True)
                    return {
                        'success': False,
                        'created': 0,
                        'updated': 0,
                        'errors': [f"Dependency exception: {e}"]
                    }
                return _run_syncer('object')

            def _run_violation_after_category():
                try:
                    category_result = futures['category'].result()
                    if not category_result.get('success', True):
                        return {
                            'success': False,
                            'created': 0,
                            'updated': 0,
                            'errors': [f"Dependency failed: category sync failed, violation sync skipped"]
                        }
                except Exception as e:
                    logger.error(f"Category sync failed, skipping violation sync: {e}", exc_info=True)
                    return {
                        'success': False,
                        'created': 0,
                        'updated': 0,
                        'errors': [f"Dependency exception: {e}"]
                    }
                return _run_syncer('violation')

            futures['object'] = executor.submit(_run_object_after_city)
            futures['violation'] = executor.submit(_run_violation_after_category)

            # Собираем результаты по мере завершения
            for finished in as_completed(list(futures.values())):
                # Найдём ключ по future
                key = None
                for k, f in futures.items():
                    if f is finished:
                        key = k
                        break

                try:
                    result = finished.result()
                except Exception as e:
                    # На всякий случай — если future бросил исключение
                    logger.error(f"Future for {key} raised exception: {e}", exc_info=True)
                    result = {
                        'success': False,
                        'created': 0,
                        'updated': 0,
                        'errors': [str(e)]
                    }

                # Сохраняем результат
                results['syncers'][key] = result
                results['summary']['total_created'] += result.get('created', 0)
                results['summary']['total_updated'] += result.get('updated', 0)
                results['summary']['total_errors'] += len(result.get('errors', []))
                if not result.get('success', True):
                    results['success'] = False

        finally:
            executor.shutdown(wait=True)
        
        logger.info(f"Синхронизация завершена. Создано: {results['summary']['total_created']}, "
                   f"Обновлено: {results['summary']['total_updated']}, "
                   f"Ошибок: {results['summary']['total_errors']}")
        
        return results
    
    def sync(self, syncer_keys: List[str]) -> Dict[str, Any]:
        """
        Синхронизация выбранных справочников
        
        Args:
            syncer_keys: Список ключей справочников для синхронизации
                        (например, ['city', 'object'])
        
        Returns:
            Словарь с результатами синхронизации
        """
        logger.info(f"Начало синхронизации справочников: {', '.join(syncer_keys)}")
        
        results = {
            'success': True,
            'syncers': {},
            'summary': {
                'total_created': 0,
                'total_updated': 0,
                'total_errors': 0
            }
        }
        
        # Определяем порядок синхронизации с учетом зависимостей
        all_sync_order = ['city', 'category', 'object', 'violation', 'user']
        sync_order = [key for key in all_sync_order if key in syncer_keys]
        
        # Добавляем оставшиеся ключи в конец
        for key in syncer_keys:
            if key not in sync_order:
                sync_order.append(key)
        
        for syncer_key in sync_order:
            if syncer_key not in self.SYNCERS:
                logger.warning(f"Неизвестный справочник: {syncer_key}")
                results['syncers'][syncer_key] = {
                    'success': False,
                    'created': 0,
                    'updated': 0,
                    'errors': [f'Неизвестный справочник: {syncer_key}']
                }
                continue
            
            try:
                syncer_class = self.SYNCERS[syncer_key]
                syncer = syncer_class(self.bitrix_client)
                result = syncer.sync()
                
                results['syncers'][syncer_key] = result
                results['summary']['total_created'] += result.get('created', 0)
                results['summary']['total_updated'] += result.get('updated', 0)
                results['summary']['total_errors'] += len(result.get('errors', []))
                
                if not result.get('success', True):
                    results['success'] = False
                    
            except Exception as e:
                logger.error(f"Ошибка при синхронизации {syncer_key}: {e}", exc_info=True)
                results['syncers'][syncer_key] = {
                    'success': False,
                    'created': 0,
                    'updated': 0,
                    'errors': [str(e)]
                }
                results['summary']['total_errors'] += 1
                results['success'] = False
        
        return results
