#!/usr/bin/env python3
"""
CLI интерфейс для синхронизации справочников с Bitrix24
"""
import argparse
import sys
import logging
from typing import List
from app.sync_engine import SyncEngine
from app.bitrix_client import Bitrix24Client
from app.config import Config
from app.form_export import run_export

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def print_results(results: dict):
    """Вывод результатов синхронизации"""
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ СИНХРОНИЗАЦИИ")
    print("=" * 60)
    
    if results.get('success'):
        print("✓ Синхронизация завершена успешно\n")
    else:
        print("✗ Синхронизация завершена с ошибками\n")
    
    # Выводим результаты по каждому справочнику
    for syncer_key, syncer_result in results.get('syncers', {}).items():
        print(f"\n{syncer_key.upper()}:")
        if syncer_result.get('success'):
            print(f"  ✓ Успешно")
        else:
            print(f"  ✗ Ошибка")
        print(f"  Создано: {syncer_result.get('created', 0)}")
        print(f"  Обновлено: {syncer_result.get('updated', 0)}")
        
        errors = syncer_result.get('errors', [])
        if errors:
            print(f"  Ошибок: {len(errors)}")
            for error in errors[:5]:  # Показываем первые 5 ошибок
                print(f"    - {error}")
            if len(errors) > 5:
                print(f"    ... и еще {len(errors) - 5} ошибок")
    
    # Итоговая статистика
    summary = results.get('summary', {})
    print("\n" + "-" * 60)
    print("ИТОГО:")
    print(f"  Всего создано: {summary.get('total_created', 0)}")
    print(f"  Всего обновлено: {summary.get('total_updated', 0)}")
    print(f"  Всего ошибок: {summary.get('total_errors', 0)}")
    print("=" * 60 + "\n")


def main():
    """Главная функция CLI"""
    parser = argparse.ArgumentParser(
        description='Синхронизация справочников с Bitrix24',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Синхронизация всех справочников
  python cli.py

  # Синхронизация только городов
  python cli.py --sync city

  # Синхронизация нескольких справочников
  python cli.py --sync city object category

  # Экспорт заявок из form_submissions в Bitrix (IBLOCK_ID=125)
  python cli.py --export

Доступные справочники:
  city, cities          - Города
  object, objects       - Объекты
  category, categories  - Категории нарушений
  violation, violations - Нарушения
  user, users           - Пользователи
        """
    )
    
    parser.add_argument(
        '--sync',
        nargs='+',
        metavar='SPR',
        help='Список справочников для синхронизации. Если не указан, синхронизируются все.'
    )
    
    parser.add_argument(
        '--webhook-url',
        type=str,
        help='URL webhook Bitrix24 (переопределяет значение из .env)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Подробный вывод (уровень DEBUG)'
    )
    parser.add_argument(
        '--export',
        action='store_true',
        help='Выгрузить заявки из form_submissions в Bitrix (IBLOCK_ID=125) и удалить выгруженные'
    )
    
    args = parser.parse_args()
    
    # Устанавливаем уровень логирования
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Проверяем конфигурацию
    webhook_url = args.webhook_url or Config.BITRIX_WEBHOOK_URL
    if not webhook_url:
        print("ОШИБКА: Не указан BITRIX_WEBHOOK_URL")
        print("Укажите его в переменной окружения, .env файле или через --webhook-url")
        sys.exit(1)
    
    try:
        bitrix_client = Bitrix24Client(webhook_url=webhook_url)
        
        if args.export:
            print("Экспорт заявок в Bitrix24 (IBLOCK_ID=125)...")
            export_result = run_export(bitrix_client=bitrix_client)
            print("\n" + "=" * 60)
            print("РЕЗУЛЬТАТЫ ЭКСПОРТА ЗАЯВОК")
            print("=" * 60)
            if export_result.get('success') and not export_result.get('errors'):
                print("✓ Экспорт завершён успешно")
            else:
                print("✗ Экспорт завершён с ошибками" if export_result.get('errors') else "✓ Экспорт завершён")
            print(f"  Выгружено: {export_result.get('exported', 0)}")
            print(f"  Удалено из БД: {export_result.get('deleted', 0)}")
            if export_result.get('errors'):
                print(f"  Ошибок: {len(export_result['errors'])}")
                for err in export_result['errors'][:5]:
                    print(f"    - {err}")
            print("=" * 60 + "\n")
            sys.exit(0 if (export_result.get('success') and not export_result.get('errors')) else 1)
        
        engine = SyncEngine(bitrix_client=bitrix_client)
        if args.sync:
            print(f"Синхронизация справочников: {', '.join(args.sync)}")
            results = engine.sync(args.sync)
        else:
            print("Синхронизация всех справочников...")
            results = engine.sync_all()
        
        print_results(results)
        sys.exit(0 if results.get('success') else 1)
        
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        print(f"\nОШИБКА: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()


print("test")
a = 1