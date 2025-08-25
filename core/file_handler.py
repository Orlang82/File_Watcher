"""
Модуль для обработки файлов: копирование, проверка стабильности, мониторинг системы
"""

import shutil
import time
import logging
from pathlib import Path
from datetime import datetime

from config.settings import (
    DEST_BASE, STABILITY_CHECK_INTERVAL, MAX_COPY_ATTEMPTS,
    NETWORK_ERROR_CODES, MAX_NETWORK_ERRORS, MIN_FREE_SPACE
)

logger = logging.getLogger(__name__)

logger.info("=== ЗАГРУЖЕН ОБНОВЛЕННЫЙ file_handler.py v2.1 ===")

def wait_for_file_stability(file_path: Path, max_wait_time=10):
    """
    Ожидает стабилизации файла (перестанет изменяться размер).
    Возвращает True если файл стабилен, False если превышено время ожидания.
    
    Args:
        file_path (Path): Путь к файлу
        max_wait_time (int): Максимальное время ожидания в секундах
        
    Returns:
        bool: True если файл стабилизирован, False если превышено время ожидания
    """
    start_time = time.time()
    previous_size = None
    network_error_count = 0
    
    while time.time() - start_time < max_wait_time:
        try:
            current_size = file_path.stat().st_size
            network_error_count = 0  # Сбрасываем счетчик при успехе
            
            if previous_size is not None and previous_size == current_size:
                logger.debug(f"Файл {file_path.name} стабилен, размер: {current_size}")
                return True
            previous_size = current_size
            time.sleep(STABILITY_CHECK_INTERVAL)
            
        except FileNotFoundError:
            logger.warning(f"Файл {file_path} исчез во время ожидания стабилизации")
            return False
            
        except OSError as e:
            # Обрабатываем сетевые ошибки (коды 59, 53, 64, и др.)
            if e.winerror in NETWORK_ERROR_CODES:
                network_error_count += 1
                logger.warning(f"Сетевая ошибка при проверке {file_path.name} (попытка {network_error_count}/{MAX_NETWORK_ERRORS}): {e}")
                
                if network_error_count >= MAX_NETWORK_ERRORS:
                    logger.error(f"Превышено количество сетевых ошибок для {file_path.name}")
                    return False
                
                # Увеличиваем задержку при сетевых ошибках
                time.sleep(min(2 * network_error_count, 5))
                continue
            else:
                logger.error(f"Ошибка при проверке стабильности файла {file_path}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке стабильности файла {file_path}: {e}")
            return False
    
    logger.warning(f"Превышено время ожидания стабилизации для файла {file_path.name}")
    return False

def copy_file_with_retries(src_path: Path, dest_path: Path, max_attempts=MAX_COPY_ATTEMPTS):
    """
    Копирует файл с несколькими попытками в случае неудачи.
    
    Args:
        src_path (Path): Путь к исходному файлу
        dest_path (Path): Путь назначения
        max_attempts (int): Максимальное количество попыток
        
    Returns:
        bool: True если копирование успешно, False в противном случае
    """
    for attempt in range(1, max_attempts + 1):
        try:
            # Проверяем существование файла с обработкой сетевых ошибок
            file_exists = False
            for check_attempt in range(3):
                try:
                    file_exists = src_path.exists()
                    break
                except OSError as e:
                    if e.winerror in NETWORK_ERROR_CODES and check_attempt < 2:
                        logger.debug(f"Сетевая ошибка при проверке существования файла, повтор...")
                        time.sleep(1)
                        continue
                    raise
            
            if not file_exists:
                logger.error(f"Исходный файл не существует: {src_path}")
                return False
                
            # Проверяем доступность файла для чтения с retry логикой
            read_success = False
            for read_attempt in range(3):
                try:
                    with open(src_path, 'rb') as f:
                        f.read(1)  # Читаем первый байт для проверки доступности
                    read_success = True
                    break
                except OSError as e:
                    if e.winerror in NETWORK_ERROR_CODES and read_attempt < 2:
                        logger.debug(f"Сетевая ошибка при чтении файла, повтор через {read_attempt + 1} сек...")
                        time.sleep(read_attempt + 1)
                        continue
                    raise
            
            if not read_success:
                logger.warning(f"Не удалось прочитать файл {src_path.name} для проверки доступности")
                if attempt < max_attempts:
                    time.sleep(2 * attempt)
                    continue
                return False
            
            # Копируем файл
            shutil.copy2(src_path, dest_path)
            logger.info(f"Файл {src_path.name} успешно скопирован в {dest_path.parent}")
            try:
                file_size = dest_path.stat().st_size
                size_mb = file_size / (1024 * 1024)
                if file_size < 1024:
                    logger.info(f"📏 Размер файла: {file_size} байт")
                elif file_size < 1024 * 1024:
                    logger.info(f"📏 Размер файла: {file_size / 1024:.1f} KB")
                else:
                    logger.info(f"📏 Размер файла: {size_mb:.2f} MB")
            except Exception as e:
                logger.debug(f"Не удалось получить размер файла: {e}")
            return True
            
        except PermissionError as e:
            logger.warning(f"Попытка {attempt}/{max_attempts}: Нет доступа к файлу {src_path.name}: {e}")
            if attempt < max_attempts:
                time.sleep(1 * attempt)
        except FileNotFoundError as e:
            logger.error(f"Попытка {attempt}/{max_attempts}: Файл не найден {src_path.name}: {e}")
            if attempt < max_attempts:
                time.sleep(0.5 * attempt)
        except OSError as e:
            # Специальная обработка сетевых ошибок
            if e.winerror in NETWORK_ERROR_CODES:
                logger.warning(f"Попытка {attempt}/{max_attempts}: Сетевая ошибка при копировании {src_path.name}: {e}")
                if attempt < max_attempts:
                    time.sleep(3 * attempt)  # Больше времени для сетевых ошибок
            else:
                logger.error(f"Попытка {attempt}/{max_attempts}: Ошибка ОС при копировании {src_path.name}: {e}")
                if attempt < max_attempts:
                    time.sleep(1 * attempt)
        except Exception as e:
            logger.error(f"Попытка {attempt}/{max_attempts}: Неожиданная ошибка при копировании {src_path.name}: {e}")
            if attempt < max_attempts:
                time.sleep(1 * attempt)
    
    logger.error(f"Не удалось скопировать файл {src_path.name} после {max_attempts} попыток")
    return False

def create_dest_directory():
    """
    Создает директорию назначения с датой.
    
    Returns:
        Path: Путь к созданной директории или None при ошибке
    """
    try:
        today_str = datetime.now().strftime("%d-%m-%Y")
        dest_dir = Path(DEST_BASE) / today_str
        dest_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Директория назначения: {dest_dir}")
        return dest_dir
    except Exception as e:
        logger.error(f"Не удалось создать директорию {dest_dir}: {e}")
        return None

def daemon_heartbeat():
    """
    Периодическая проверка работоспособности системы.
    
    Returns:
        bool: True если система работает нормально, False при проблемах
    """
    try:
        # Проверяем свободное место на диске
        free_space = shutil.disk_usage(DEST_BASE).free
        if free_space < MIN_FREE_SPACE:
            logger.warning(f"Мало свободного места на диске: {free_space / (1024**3):.2f} GB")
        
        logger.debug("Процесс работает нормально")
        return True
    except Exception as e:
        logger.warning(f"Проблема при проверке состояния: {e}")
        return False

def monitor_observer_health(observers):
    """
    Мониторит состояние наблюдателей и перезапускает их при необходимости.
    
    Args:
        observers (list): Список кортежей (observer, config)
    """
    from watchdog.observers import Observer
    
    for i, (observer, config) in enumerate(observers):
        try:
            if not observer.is_alive():
                logger.warning(f"Наблюдатель {i+1} не активен. Попытка перезапуска...")
                
                try:
                    observer.stop()
                    observer.join(timeout=5)
                except:
                    pass
                
                # Импортируем здесь чтобы избежать циклических импортов
                from core.watcher import MultiDirHandler
                
                path = config["watch_dir"]
                conditions = config["conditions"]
                handler = MultiDirHandler(conditions)
                new_observer = Observer()
                new_observer.schedule(handler, path, recursive=True)
                new_observer.start()
                
                observers[i] = (new_observer, config)
                logger.info(f"Наблюдатель {i+1} перезапущен для: {path}")
                
        except Exception as e:
            logger.error(f"Ошибка при мониторинге наблюдателя {i+1}: {e}")

def check_file_size(file_path: Path, min_size=1024):
    """
    Проверяет что файл имеет минимальный размер.
    
    Args:
        file_path (Path): Путь к файлу
        min_size (int): Минимальный размер в байтах (по умолчанию 1KB)
        
    Returns:
        bool: True если размер достаточный
    """
    try:
        size = file_path.stat().st_size
        if size < min_size:
            logger.warning(f"Файл {file_path.name} слишком мал ({size} байт), возможно не завершен")
            return False
        logger.debug(f"Размер файла {file_path.name}: {size} байт")
        return True
    except Exception as e:
        logger.error(f"Ошибка проверки размера файла {file_path.name}: {e}")
        return False
