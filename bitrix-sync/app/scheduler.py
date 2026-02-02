import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Optional
from app.sync_engine import SyncEngine
from app.bitrix_client import Bitrix24Client
from app.config import Config
from app.form_export import run_export

logger = logging.getLogger(__name__)


class SyncScheduler:
    """Планировщик задач синхронизации"""
    
    def __init__(self, sync_schedule: Optional[str] = None):
        """
        Инициализация планировщика
        
        Args:
            sync_schedule: Расписание в cron-формате (например, "0 * * * *")
                          Если не указано, берется из Config.SYNC_SCHEDULE
        """
        self.scheduler = BlockingScheduler()
        self.sync_schedule = sync_schedule or Config.SYNC_SCHEDULE
        self.export_schedule = getattr(Config, 'EXPORT_SCHEDULE', '* * * * *')
        self.engine = SyncEngine()
        
        # Парсим cron-расписание
        self.cron_parts = self._parse_cron_schedule(self.sync_schedule)
        self.export_cron_parts = self._parse_cron_schedule(self.export_schedule)
    
    def _parse_cron_schedule(self, schedule: str) -> dict:
        """
        Парсинг cron-расписания в формат для APScheduler
        
        Args:
            schedule: Cron-расписание (например, "0 * * * *")
            
        Returns:
            Словарь с параметрами для CronTrigger
        """
        parts = schedule.strip().split()
        
        if len(parts) != 5:
            logger.warning(f"Неверный формат cron-расписания: {schedule}. Используется значение по умолчанию.")
            return {'minute': '0', 'hour': '*', 'day': '*', 'month': '*', 'day_of_week': '*'}
        
        return {
            'minute': parts[0],
            'hour': parts[1],
            'day': parts[2],
            'month': parts[3],
            'day_of_week': parts[4]
        }
    
    def sync_job(self):
        """Задача синхронизации"""
        try:
            logger.info("Запуск запланированной синхронизации")
            results = self.engine.sync_all()
            
            if results.get('success'):
                logger.info(f"Синхронизация завершена успешно. "
                           f"Создано: {results['summary']['total_created']}, "
                           f"Обновлено: {results['summary']['total_updated']}")
            else:
                logger.warning(f"Синхронизация завершена с ошибками. "
                             f"Ошибок: {results['summary']['total_errors']}")
        except Exception as e:
            logger.error(f"Ошибка при выполнении синхронизации: {e}", exc_info=True)

    def export_job(self):
        """Задача экспорта заявок в Bitrix (form_submissions → IBLOCK_ID=125)"""
        try:
            logger.info("Запуск экспорта заявок в Bitrix24")
            result = run_export()
            if result.get('success') and not result.get('errors'):
                logger.info(f"Экспорт завершён: выгружено {result.get('exported', 0)}, удалено {result.get('deleted', 0)}")
            elif result.get('errors'):
                logger.warning(f"Экспорт завершён с ошибками: {len(result['errors'])}")
        except Exception as e:
            logger.error(f"Ошибка при экспорте заявок: {e}", exc_info=True)
    
    def start(self):
        """Запуск планировщика"""
        # Задача синхронизации справочников
        trigger = CronTrigger(**self.cron_parts)
        self.scheduler.add_job(
            func=self.sync_job,
            trigger=trigger,
            id='sync_job',
            name='Bitrix24 синхронизация справочников',
            replace_existing=True
        )
        # Задача экспорта заявок (раз в минуту по умолчанию)
        export_trigger = CronTrigger(**self.export_cron_parts)
        self.scheduler.add_job(
            func=self.export_job,
            trigger=export_trigger,
            id='export_job',
            name='Экспорт заявок в Bitrix24 (form_submissions → IBLOCK 125)',
            replace_existing=True
        )
        
        logger.info(f"Планировщик запущен. Синхронизация: {self.sync_schedule}, экспорт заявок: {self.export_schedule}")
        logger.info("Для остановки нажмите Ctrl+C")
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Планировщик остановлен")
            self.scheduler.shutdown()
    
    def stop(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()
