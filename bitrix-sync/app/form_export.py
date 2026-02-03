"""
Экспорт заявок из form_submissions в список Bitrix24 (IBLOCK_ID=125).
После успешной выгрузки записи удаляются из БД.
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from app.bitrix_client import Bitrix24Client
from app.database import get_session, get_models
from app.config import Config

logger = logging.getLogger(__name__)


def _parse_file_path_list(file_path_value: str) -> List[str]:
    """Из значения file_path (JSON-массив путей/имён или одна строка) возвращает список имён файлов (только basename)."""
    if not file_path_value or not file_path_value.strip():
        return []
    s = file_path_value.strip()
    if s.startswith('['):
        try:
            names = json.loads(s)
            raw = [x for x in names if isinstance(x, str) and x.strip()]
        except json.JSONDecodeError:
            raw = [s] if s else []
    else:
        raw = [s] if s else []
    # В БД может быть полный путь (C:\... или /path/...); для поиска в upload_folder берём только имя файла.
    # На Linux Path("C:\...\i.webp").name вернёт всю строку (обратный слэш не разделитель), поэтому нормализуем:
    def basename_any_sep(path_str: str) -> str:
        return Path(path_str.replace('\\', '/')).name
    return [basename_any_sep(p) for p in raw]


def _resolve_file_in_uploads(upload_folder: Path, filename: str) -> Optional[Path]:
    """
    Ищет файл в upload_folder. В БД может быть клиентский путь (C:\\...\\i.webp),
    а на сервере файл сохранён как timestamp_originalname (например 1738581234_i.webp).
    Сначала проверяем точное имя, затем шаблон *_filename.
    """
    direct = upload_folder / filename
    if direct.is_file():
        return direct
    # Паттерн сохранения в routes: timestamp_filename
    candidates = list(upload_folder.glob(f"*_{filename}"))
    if candidates:
        return candidates[0]
    # Точное совпадение по имени (уже проверили выше, но на всякий случай)
    for p in upload_folder.iterdir():
        if p.is_file() and p.name == filename:
            return p
    return None


def _upload_files_for_submission(
    client: Bitrix24Client,
    file_path_value: str,
    upload_folder: Path,
) -> List[int]:
    """Загружает файлы в диск Bitrix24. file_path_value — значение form_submissions.file_path; файлы ищутся в upload_folder (uploads)."""
    filenames = _parse_file_path_list(file_path_value)
    file_ids = []
    for filename in filenames:
        full_path = _resolve_file_in_uploads(upload_folder, filename)
        if full_path is None:
            logger.warning("Файл не найден в uploads (искали %s или *_%s): %s", filename, filename, upload_folder)
            continue
        fid = client.upload_file_to_disk(str(full_path))
        if fid is not None:
            file_ids.append(fid)
        else:
            logger.warning("Не удалось загрузить файл в Bitrix: %s", full_path)
    return file_ids


# Фиксированные коды свойств списка Bitrix24 (IBLOCK_ID=125)
NAME_VALUE = "Видеофиксация"
PROPERTY_1095 = "PROPERTY_1095"   # дата из created_at
PROPERTY_1101 = "PROPERTY_1101"   # object_id (btxid)
PROPERTY_1107 = "PROPERTY_1107"   # comment
PROPERTY_1109 = "PROPERTY_1109"   # violation_id (btxid)
PROPERTY_1111 = "PROPERTY_1111"   # файл(ы) из file_path
PROPERTY_1123 = "PROPERTY_1123"   # violation_category_id (btxid)


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

        # Файлы всегда лежат в папке uploads; путь/имя берём из form_submissions.file_path
        upload_folder = Path(Config.EXPORT_UPLOAD_FOLDER)

        for sub in rows:
            try:
                # NAME — всегда "Нарушение"
                fields = {'NAME': NAME_VALUE}

                # PROPERTY_1095 — дата из created_at (формат YYYY-MM-DD)
                if sub.created_at:
                    fields[PROPERTY_1095] = sub.created_at.strftime('%Y-%m-%d')

                # PROPERTY_1101 — object_id (btxid)
                if sub.object_id is not None:
                    fields[PROPERTY_1101] = str(sub.object_id)

                # PROPERTY_1107 — comment
                fields[PROPERTY_1107] = (sub.comment or '')[:500]

                # PROPERTY_1109 — violation_id (btxid)
                if sub.violation_id is not None:
                    fields[PROPERTY_1109] = str(sub.violation_id)

                # PROPERTY_1123 — violation_category_id (btxid)
                if sub.violation_category_id is not None:
                    fields[PROPERTY_1123] = str(sub.violation_category_id)

                # PROPERTY_1111 — файл(ы): form_submissions.file_path → ищем в uploads → загружаем в Bitrix
                if sub.file_path and upload_folder and upload_folder.is_dir():
                    file_ids = _upload_files_for_submission(client, sub.file_path, upload_folder)
                    if file_ids:
                        # Bitrix список: свойство типа "файл" может принимать массив ID или один ID
                        fields[PROPERTY_1111] = {'n0':[f'n{file_ids[0]}']} if len(file_ids) == 1 else {'n0':[f'n{file_ids[0]}', f'n{file_ids[1]}']}

                element_code = str(int(time.time() * 1000))
                params = {
                    'IBLOCK_TYPE_ID': Config.EXPORT_IBLOCK_TYPE_ID,
                    'IBLOCK_ID': Config.EXPORT_IBLOCK_ID,
                    'ELEMENT_CODE': element_code,
                    'FIELDS': fields,
                }
                success = False
                error_appended = False
                api_result = None
                try:
                    api_result = client._call_method('lists.element.add', params)
                    if api_result is not None:
                        if isinstance(api_result, int) and api_result > 0:
                            success = True
                        elif isinstance(api_result, dict) and (api_result.get('ID') or api_result.get('id')):
                            success = True
                except Exception as add_err:
                    err_text = str(add_err)
                    if 'ERROR_ELEMENT_ALREADY_EXISTS' in err_text:
                        # Элемент с таким ELEMENT_CODE уже есть в Bitrix — считаем успехом и удаляем из БД
                        success = True
                        logger.info(f"Заявка #{sub.id}: элемент sub_{sub.id} уже существует в Bitrix, удаляем из БД")
                    else:
                        raise

                if success:
                    # ВРЕМЕННО: не удаляем из БД после выгрузки (вернуть по запросу)
                    # session.delete(sub)
                    # result['deleted'] += 1
                    result['exported'] += 1
                    logger.info(f"Заявка #{sub.id} выгружена в Bitrix")
                elif not error_appended:
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
