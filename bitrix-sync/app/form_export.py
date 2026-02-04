"""
Экспорт заявок из form_submissions в список Bitrix24 (IBLOCK_ID=125).
После успешной выгрузки записи удаляются из БД.
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from app.bitrix_client import Bitrix24Client
from app.database import get_session, get_models
from app.config import Config

logger = logging.getLogger(__name__)


def _parse_file_path_list(file_path_value: str) -> List[str]:
    """Из form_submissions.file_path возвращает список имён файлов. В БД хранится JSON-массив, например ["i.webp"]."""
    if not file_path_value or not file_path_value.strip():
        return []
    s = file_path_value.strip()
    raw: List[str] = []
    # В БД — JSON-массив вида ["i.webp"] или ["a.png", "b.pdf"]
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            raw = [x for x in parsed if isinstance(x, str) and x.strip()]
        elif isinstance(parsed, str) and parsed.strip():
            raw = [parsed.strip()]
    except json.JSONDecodeError:
        # На случай старого формата — одна строка без скобок
        raw = [s] if s else []
    def basename_any_sep(path_str: str) -> str:
        return Path(path_str.replace('\\', '/')).name
    return [basename_any_sep(p) for p in raw]


def _resolve_file_in_uploads(upload_folder: Path, filename: str) -> Optional[Path]:
    """
    Ищет файл в папке проекта uploads по имени из БД (например i.webp).
    Сначала точное имя, затем шаблон *_filename (если файл сохранён как 1738581234_i.webp).
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
) -> Tuple[List[int], List[Path]]:
    """Загружает один или несколько файлов в диск Bitrix24. Возвращает (список file_id, список путей загруженных файлов для последующего удаления)."""
    filenames = _parse_file_path_list(file_path_value)
    file_ids: List[int] = []
    uploaded_paths: List[Path] = []
    uploaded = 0
    for i, filename in enumerate(filenames, 1):
        full_path = _resolve_file_in_uploads(upload_folder, filename)
        if full_path is None:
            logger.warning("[файл %s/%s] Не найден в uploads: %s (искали %s или *_%s)", i, len(filenames), filename, filename, filename)
            continue
        fid = client.upload_file_to_disk(str(full_path))
        if fid is not None:
            file_ids.append(fid)
            uploaded_paths.append(full_path)
            uploaded += 1
            logger.info("[файл %s/%s] Отправлено в Bitrix: %s, file_id=%s", i, len(filenames), filename, fid)
        else:
            logger.warning("[файл %s/%s] Не отправлено в Bitrix: %s", i, len(filenames), filename)
    if filenames:
        logger.info("Итого по заявке: загружено %s из %s файлов", uploaded, len(filenames))
    return file_ids, uploaded_paths


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

        # Все файлы — в папке проекта uploads; в БД (file_path) — только имя файла, например i.webp
        upload_folder = Path(Config.EXPORT_UPLOAD_FOLDER)
        files_to_delete_after_commit: List[Path] = []

        for sub in rows:
            uploaded_paths_this_sub: List[Path] = []
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

                # PROPERTY_1111 — файл(ы): form_submissions.file_path (JSON-массив) → ищем в uploads → загружаем в Bitrix
                if sub.file_path and upload_folder and upload_folder.is_dir():
                    file_ids, uploaded_paths_this_sub = _upload_files_for_submission(client, sub.file_path, upload_folder)
                    if file_ids:
                        # Bitrix список: свойство типа "файл" — массив ID в формате n0: [n123, n456, ...]
                        fields[PROPERTY_1111] = {'n0': [f'n{fid}' for fid in file_ids]}

                element_code = str(int(time.time() * 1000))
                params = {
                    'IBLOCK_TYPE_ID': Config.EXPORT_IBLOCK_TYPE_ID,
                    'IBLOCK_ID': Config.EXPORT_IBLOCK_ID,
                    'ELEMENT_CODE': element_code,
                    'FIELDS': fields,
                }
                result_id = None
                api_result = None
                try:
                    api_result = client._call_method('lists.element.add', params)
                    if isinstance(api_result, int) and api_result > 0:
                        result_id = api_result
                    elif isinstance(api_result, dict):
                        result_id = api_result.get('ID') or api_result.get('id')
                        if isinstance(result_id, int) and result_id <= 0:
                            result_id = None  # 0 трактуем как «нет id»
                except Exception as add_err:
                    err_text = str(add_err)
                    if 'ERROR_ELEMENT_ALREADY_EXISTS' in err_text:
                        result_id = True  # элемент уже есть — считаем ок
                        logger.info(f"Заявка #{sub.id}: элемент уже существует в Bitrix")
                    else:
                        raise

                if result_id is not None:
                    session.delete(sub)
                    result['deleted'] += 1
                    result['exported'] += 1
                    files_to_delete_after_commit.extend(uploaded_paths_this_sub)
                    logger.info(f"Заявка #{sub.id} выгружена в Bitrix, result id={result_id}")
                else:
                    # result id NULL/0 — из БД не удаляем, ошибку не пишем, продолжаем в штатном режиме
                    logger.info(f"Заявка #{sub.id}: Bitrix вернул result id=NULL, пропускаем без удаления из БД")

            except Exception as e:
                result['success'] = False
                result['errors'].append(f"Заявка #{sub.id}: {e}")
                logger.error(f"Ошибка экспорта заявки #{sub.id}: {e}", exc_info=True)

        session.commit()

        # После успешного коммита удаляем с диска файлы, которые отправили в Bitrix
        for path in files_to_delete_after_commit:
            try:
                if path.is_file():
                    path.unlink(missing_ok=True)
                    logger.info("Файл удалён из uploads после отправки в Bitrix: %s", path.name)
                else:
                    logger.debug("Файл уже отсутствует в uploads: %s", path)
            except OSError as e:
                logger.warning("Не удалось удалить файл %s после отправки: %s", path, e)

        logger.info(f"Экспорт заявок завершён: выгружено {result['exported']}, удалено из БД {result['deleted']}, ошибок {len(result['errors'])}")
    except Exception as e:
        logger.error(f"Ошибка при экспорте заявок: {e}", exc_info=True)
        result['success'] = False
        result['errors'].append(str(e))
        session.rollback()
    finally:
        session.close()
    return result
