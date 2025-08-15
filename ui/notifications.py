"""
Модуль для работы с уведомлениями Windows
"""

import logging
import time
from pathlib import Path

try:
    from winotify import Notification, audio
except ImportError as e:
    logging.warning(f"Модуль winotify не найден: {e}")
    Notification = None
    audio = None

from config.settings import ICON_PATH, NOTIFICATION_APP_ID, NOTIFICATION_TITLE

logger = logging.getLogger(__name__)

def show_notification(file_name, custom_title=None, custom_message=None):
    """
    Показывает уведомление Windows о новом файле.
    
    Args:
        file_name (str): Имя файла
        custom_title (str, optional): Пользовательский заголовок
        custom_message (str, optional): Пользовательское сообщение
    """
    if not Notification:
        logger.warning("Модуль уведомлений недоступен")
        return
        
    try:
        title = custom_title or NOTIFICATION_TITLE
        message = custom_message or file_name
        
        # Проверяем существование иконки
        icon_path = ICON_PATH
        if not Path(icon_path).exists():
            logger.debug(f"Иконка не найдена по пути {icon_path}, будет использована системная")
            icon_path = None
        
        toast = Notification(
            app_id=NOTIFICATION_APP_ID, 
            title=title, 
            msg=message, 
            icon=icon_path
        )
        
        # Устанавливаем звук уведомления
        if audio:
            toast.set_audio(audio.Default, loop=False)
        
        toast.show()
        time.sleep(0.1)  # Небольшая задержка для корректного отображения
        
        logger.info(f"Показано уведомление для файла: {file_name}")
        
    except Exception as e:
        logger.warning(f"Не удалось показать уведомление для {file_name}: {e}")

def show_status_notification(title, message, duration=5):
    """
    Показывает статусное уведомление.
    
    Args:
        title (str): Заголовок уведомления
        message (str): Текст сообщения
        duration (int): Длительность показа в секундах
    """
    if not Notification:
        logger.warning("Модуль уведомлений недоступен")
        return
        
    try:
        # Проверяем существование иконки
        icon_path = ICON_PATH
        if not Path(icon_path).exists():
            icon_path = None
        
        toast = Notification(
            app_id=NOTIFICATION_APP_ID,
            title=title,
            msg=message,
            icon=icon_path,
            duration="short" if duration <= 5 else "long"
        )
        
        toast.show()
        logger.info(f"Показано статусное уведомление: {title}")
        
    except Exception as e:
        logger.warning(f"Не удалось показать статусное уведомление '{title}': {e}")

def show_startup_notification():
    """
    Показывает уведомление о запуске приложения.
    """
    show_status_notification(
        title="📊 File Watcher",
        message="Фоновый мониторинг файлов запущен",
        duration=3
    )

def show_shutdown_notification():
    """
    Показывает уведомление о завершении работы приложения.
    """
    show_status_notification(
        title="📊 File Watcher",
        message="Мониторинг файлов остановлен",
        duration=3
    )

def show_error_notification(error_message):
    """
    Показывает уведомление об ошибке.
    
    Args:
        error_message (str): Текст ошибки
    """
    show_status_notification(
        title="❌ File Watcher - Ошибка",
        message=error_message,
        duration=10
    )

def show_restart_notification(active_watchers, total_watchers):
    """
    Показывает уведомление о перезапуске наблюдателей.
    
    Args:
        active_watchers (int): Количество активных наблюдателей
        total_watchers (int): Общее количество наблюдателей
    """
    show_status_notification(
        title="🔄 File Watcher",
        message=f"Наблюдатели перезапущены ({active_watchers}/{total_watchers} активны)",
        duration=5
    )
