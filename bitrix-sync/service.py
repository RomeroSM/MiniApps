#!/usr/bin/env python3
"""
Сервисный режим для автоматической синхронизации справочников с Bitrix24
"""
import sys
import logging
import signal
from app.scheduler import SyncScheduler
from app.config import Config

# Настройка логирования
# В Docker логи идут в stdout/stderr, чтобы их можно было видеть через docker-compose logs
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Глобальная переменная для планировщика
scheduler = None


def signal_handler(sig, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info("Получен сигнал завершения, останавливаем планировщик...")
    if scheduler:
        scheduler.stop()
    sys.exit(0)


def main():
    """Главная функция сервиса"""
    global scheduler
    
    # Проверяем конфигурацию
    if not Config.BITRIX_WEBHOOK_URL:
        logger.error("BITRIX_WEBHOOK_URL не указан в конфигурации")
        sys.exit(1)
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Создаем и запускаем планировщик
        scheduler = SyncScheduler()
        
        logger.info("Запуск сервиса синхронизации Bitrix24")
        logger.info(f"Webhook URL: {Config.BITRIX_WEBHOOK_URL}")
        logger.info(f"Расписание: {Config.SYNC_SCHEDULE}")
        
        # Запускаем планировщик (блокирующий вызов)
        scheduler.start()
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if scheduler:
            scheduler.stop()


if __name__ == '__main__':
    main()
