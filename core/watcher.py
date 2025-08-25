"""
Модуль для мониторинга файловой системы
"""

import logging
import threading
import time
from pathlib import Path
from watchdog.events import FileSystemEventHandler

from config.settings import COPY_DELAY
from .file_handler import wait_for_file_stability, copy_file_with_retries, create_dest_directory
from .file_handler import check_file_size

logger = logging.getLogger(__name__)

logger.info("=== ЗАГРУЖЕН ОБНОВЛЕННЫЙ watcher.py v2.1 ===")

class MultiDirHandler(FileSystemEventHandler):
    """
    Обработчик событий файловой системы для нескольких директорий.
    Отслеживает создание и изменение файлов, применяет условия фильтрации
    и обрабатывает подходящие файлы.
    """
    
    def __init__(self, conditions):
        """
        Инициализация обработчика.
        
        Args:
            conditions (list): Список функций-условий для фильтрации файлов
        """
        super().__init__()
        self.conditions = conditions
        self.processed_files = set()
        self.pending_files = {}
        self.lock = threading.Lock()
        
        logger.debug(f"Создан обработчик с {len(conditions)} условиями фильтрации")

    def should_process_file(self, file_path: Path):
        """
        Проверяет, нужно ли обрабатывать файл согласно условиям фильтрации.
        
        Args:
            file_path (Path): Путь к файлу
            
        Returns:
            bool: True если файл соответствует условиям, False в противном случае
        """
        file_name_lower = file_path.name.lower()
        result = any(cond(file_name_lower) for cond in self.conditions)
        
        if result:
            logger.debug(f"Файл {file_path.name} соответствует условиям фильтрации")
        
        return result

    def process_file(self, file_path: Path, event_type="unknown"):
        """
        Обрабатывает файл: проверяет условия и копирует если необходимо.
        
        Args:
            file_path (Path): Путь к файлу
            event_type (str): Тип события (created, modified, etc.)
        """
        file_key = str(file_path)
        
        # Проверяем не обрабатывался ли файл уже
        with self.lock:
            if file_key in self.processed_files:
                logger.debug(f"Файл {file_path.name} уже был обработан")
                return
            
        # Проверяем соответствие условиям фильтрации
        if not self.should_process_file(file_path):
            logger.debug(f"Файл {file_path.name} не соответствует условиям фильтрации")
            return

        logger.info(f"Обнаружен файл для обработки: {file_path.name} (событие: {event_type})")
        
        try:
            # Ждем стабилизации файла
            logger.debug(f"Ожидание стабилизации файла {file_path.name}...")
            time.sleep(COPY_DELAY)

            if not wait_for_file_stability(file_path, max_wait_time=25):  # Ожидание стабилизации увеличено до 25 сек.
                logger.warning(f"Файл {file_path.name} не стабилизировался, пропускаем")
                return
            
            # Добавляем проверку размера
            if not check_file_size(file_path):
                logger.warning(f"Файл {file_path.name} имеет недостаточный размер, пропускаем")
                return

            # Показываем уведомление (импортируем здесь чтобы избежать циклических импортов)
            try:
                from ui.notifications import show_notification
                show_notification(file_path.name)
            except ImportError as e:
                logger.warning(f"Не удалось загрузить модуль уведомлений: {e}")
            
            # Создаем директорию назначения
            dest_dir = create_dest_directory()
            if not dest_dir:
                logger.error(f"Не удалось создать директорию назначения для {file_path.name}")
                return

            # Копируем файл
            dest_path = dest_dir / file_path.name
            if copy_file_with_retries(file_path, dest_path):
                with self.lock:
                    self.processed_files.add(file_key)
                    
                    # Очищаем список обработанных файлов если он стал слишком большим
                    if len(self.processed_files) > 1000:
                        self.processed_files.clear()
                        logger.info("Очищен список обработанных файлов")
                        
                logger.info(f"✅ Файл {file_path.name} успешно обработан")
            else:
                logger.error(f"❌ Не удалось обработать файл {file_path.name}")
                
        except Exception as e:
            logger.error(f"Ошибка при обработке файла {file_path.name}: {e}")

    def on_created(self, event):
        """
        Обработка события создания файла.
        
        Args:
            event: Событие файловой системы
        """
        if not event.is_directory:
            file_path = Path(event.src_path)
            logger.debug(f"Событие создания файла: {file_path.name}")
            self.process_file(file_path, "created")

    def on_modified(self, event):
        """
        Обработка события изменения файла.
        
        Args:
            event: Событие файловой системы
        """
        if not event.is_directory:
            file_path = Path(event.src_path)
            
            # Проверяем соответствие условиям перед запуском отложенной обработки
            if self.should_process_file(file_path):
                logger.debug(f"Событие изменения файла: {file_path.name}")
                
                def delayed_process():
                    """Отложенная обработка для события изменения"""
                    time.sleep(2)  # Дополнительная задержка для события изменения
                    self.process_file(file_path, "modified")
                
                # Запускаем обработку в отдельном потоке
                threading.Thread(target=delayed_process, daemon=True).start()

    def get_stats(self):
        """
        Возвращает статистику работы обработчика.
        
        Returns:
            dict: Словарь со статистикой
        """
        with self.lock:
            return {
                'processed_files_count': len(self.processed_files),
                'pending_files_count': len(self.pending_files),
                'conditions_count': len(self.conditions)
            }

    def clear_processed_files(self):
        """
        Очищает список обработанных файлов.
        """
        with self.lock:
            count = len(self.processed_files)
            self.processed_files.clear()
            logger.info(f"Очищен список из {count} обработанных файлов")
