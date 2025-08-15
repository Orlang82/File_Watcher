"""
Модуль системного трея для управления приложением
"""

import logging
import os
from pathlib import Path

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError as e:
    logging.warning(f"Модули pystray или PIL не найдены: {e}")
    pystray = None
    Image = None
    ImageDraw = None

from config.settings import ICON_PATH, LOG_DIR
from .notifications import show_status_notification, show_restart_notification

logger = logging.getLogger(__name__)

class TrayApp:
    """
    Приложение системного трея для управления файловым мониторингом.
    """
    
    def __init__(self):
        """Инициализация приложения трея."""
        self.observers = []
        self.icon = None
        self.running = True
        
        logger.debug("Инициализировано приложение системного трея")

    def create_tray_icon(self):
        """
        Создает иконку для системного трея.
        
        Returns:
            PIL.Image: Изображение иконки
        """
        if not Image or not ImageDraw:
            logger.warning("PIL недоступен, иконка трея не будет создана")
            return None
            
        try:
            # Пытаемся загрузить существующую иконку
            if Path(ICON_PATH).exists():
                image = Image.open(ICON_PATH)
                if image.size != (64, 64):
                    image = image.resize((64, 64), Image.Resampling.LANCZOS)
                logger.debug(f"Загружена иконка из файла: {ICON_PATH}")
                return image
        except Exception as e:
            logger.debug(f"Не удалось загрузить иконку из {ICON_PATH}: {e}")
        
        # Создаем простую иконку программно
        try:
            image = Image.new('RGB', (64, 64), color='blue')
            draw = ImageDraw.Draw(image)
            
            # Рисуем простой символ папки
            draw.rectangle([10, 20, 54, 50], fill='lightblue', outline='darkblue', width=2)
            draw.rectangle([15, 15, 35, 25], fill='lightblue', outline='darkblue', width=2)
            
            # Добавляем символ "глаза" для мониторинга
            draw.ellipse([20, 30, 30, 40], fill='white', outline='black')
            draw.ellipse([23, 33, 27, 37], fill='black')
            
            logger.debug("Создана программная иконка трея")
            return image
            
        except Exception as e:
            logger.error(f"Не удалось создать программную иконку: {e}")
            return None

    def setup_tray(self):
        """Настройка иконки в системном трее."""
        if not pystray:
            logger.warning("pystray недоступен, системный трей не будет создан")
            return False
            
        try:
            image = self.create_tray_icon()
            if not image:
                logger.error("Не удалось создать иконку для трея")
                return False
            
            menu = pystray.Menu(
                pystray.MenuItem("📊 Статус", self.show_status),
                pystray.MenuItem("📋 Открыть логи", self.open_logs),
                pystray.MenuItem("🔄 Перезапустить", self.restart_watchers),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("❌ Выход", self.quit_app)
            )
            
            self.icon = pystray.Icon(
                "FileWatcher", 
                image, 
                "File Watcher - Мониторинг файлов", 
                menu
            )
            
            logger.info("Системный трей настроен успешно")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при настройке системного трея: {e}")
            return False
        
    def show_status(self, icon=None, item=None):
        """
        Показывает статус работы наблюдателей.
        
        Args:
            icon: Иконка трея (параметр pystray)
            item: Элемент меню (параметр pystray)
        """
        try:
            active_watchers = sum(1 for obs, _ in self.observers if obs.is_alive())
            total_watchers = len(self.observers)
            
            # Собираем статистику по каждому наблюдателю
            status_details = []
            for i, (observer, config) in enumerate(self.observers):
                status = "🟢 Активен" if observer.is_alive() else "🔴 Неактивен"
                description = config.get('description', f'Наблюдатель {i+1}')
                status_details.append(f"{status} {description}")
            
            status_message = f"Активных наблюдателей: {active_watchers}/{total_watchers}"
            if status_details:
                status_message += f"\n{chr(10).join(status_details[:3])}"  # Показываем первые 3
                if len(status_details) > 3:
                    status_message += f"\n... и еще {len(status_details) - 3}"
            
            show_status_notification(
                title="📊 File Watcher - Статус",
                message=status_message,
                duration=8
            )
            
            logger.info(f"Показан статус: {active_watchers}/{total_watchers} активных наблюдателей")
            
        except Exception as e:
            logger.error(f"Ошибка при показе статуса: {e}")
            show_status_notification(
                title="❌ Ошибка",
                message="Не удалось получить статус",
                duration=5
            )
        
    def open_logs(self, icon=None, item=None):
        """
        Открывает папку с логами.
        
        Args:
            icon: Иконка трея (параметр pystray)
            item: Элемент меню (параметр pystray)
        """
        try:
            if LOG_DIR.exists():
                os.startfile(str(LOG_DIR))
                logger.info(f"Открыта папка с логами: {LOG_DIR}")
            else:
                logger.warning(f"Папка с логами не существует: {LOG_DIR}")
                show_status_notification(
                    title="⚠️ Предупреждение",
                    message="Папка с логами не найдена",
                    duration=5
                )
        except Exception as e:
            logger.error(f"Не удалось открыть папку с логами: {e}")
            show_status_notification(
                title="❌ Ошибка",
                message="Не удалось открыть папку с логами",
                duration=5
            )
            
    def restart_watchers(self, icon=None, item=None):
        """
        Перезапускает всех наблюдателей.
        
        Args:
            icon: Иконка трея (параметр pystray)
            item: Элемент меню (параметр pystray)
        """
        try:
            logger.info("Инициирован перезапуск наблюдателей из системного трея...")
            
            # Импортируем здесь чтобы избежать циклических импортов
            from core.file_handler import monitor_observer_health
            
            monitor_observer_health(self.observers)
            
            # Подсчитываем активных наблюдателей после перезапуска
            active_watchers = sum(1 for obs, _ in self.observers if obs.is_alive())
            total_watchers = len(self.observers)
            
            show_restart_notification(active_watchers, total_watchers)
            logger.info(f"Перезапуск завершен: {active_watchers}/{total_watchers} активных наблюдателей")
            
        except Exception as e:
            logger.error(f"Ошибка при перезапуске наблюдателей: {e}")
            show_status_notification(
                title="❌ Ошибка",
                message="Не удалось перезапустить наблюдателей",
                duration=5
            )
        
    def quit_app(self, icon=None, item=None):
        """
        Завершает работу приложения.
        
        Args:
            icon: Иконка трея (параметр pystray)
            item: Элемент меню (параметр pystray)
        """
        try:
            logger.info("Инициировано завершение работы из системного трея...")
            
            # Устанавливаем флаг завершения
            import config.settings
            config.settings.RUNNING = False
            self.running = False
            
            # Останавливаем иконку трея
            if self.icon:
                self.icon.stop()
                
            # Показываем уведомление о завершении
            from .notifications import show_shutdown_notification
            show_shutdown_notification()
            
        except Exception as e:
            logger.error(f"Ошибка при завершении работы: {e}")

    def run(self):
        """
        Запускает системный трей (блокирующий вызов).
        
        Returns:
            bool: True если трей был запущен успешно
        """
        if not self.icon:
            logger.error("Иконка трея не настроена")
            return False
            
        try:
            logger.info("Запуск системного трея...")
            self.icon.run()  # Блокирующий вызов
            return True
        except Exception as e:
            logger.error(f"Ошибка при запуске системного трея: {e}")
            return False

    def stop(self):
        """Останавливает системный трей."""
        try:
            if self.icon:
                self.icon.stop()
                logger.info("Системный трей остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке системного трея: {e}")

    def get_stats(self):
        """
        Возвращает статистику работы наблюдателей.
        
        Returns:
            dict: Словарь со статистикой
        """
        try:
            active_count = sum(1 for obs, _ in self.observers if obs.is_alive())
            return {
                'total_observers': len(self.observers),
                'active_observers': active_count,
                'inactive_observers': len(self.observers) - active_count,
                'tray_running': self.running and self.icon is not None
            }
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {
                'total_observers': 0,
                'active_observers': 0,
                'inactive_observers': 0,
                'tray_running': False
            }
