"""
Главный модуль файлового мониторинга STAT
Система мониторинга файлов с автоматическим копированием в целевую директорию

Автор: Risk Management Department
Версия: 2.0 (модульная)
"""

import sys
import logging
import threading
import time
import signal
from pathlib import Path

# Настройка кодировки stdout/stderr для корректного вывода в Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Импорты модулей проекта
try:
    from config.settings import LOG_DIR, LOG_MAX_BYTES, LOG_BACKUP_COUNT
    from config.watch_rules import WATCH_CONFIGS, get_watch_paths
    from core.watcher import MultiDirHandler
    from core.file_handler import daemon_heartbeat, monitor_observer_health
    from core.utils import validate_paths, test_filename_conditions
    from ui.tray_app import TrayApp
    from ui.notifications import show_startup_notification, show_error_notification
except ImportError as e:
    print(f"❌ Ошибка импорта модулей: {e}")
    print("Убедитесь, что все модули находятся в правильных директориях")
    print("Структура должна быть:")
    print("  watcher/")
    print("    ├── main.py")
    print("    ├── config/")
    print("    ├── core/")
    print("    └── ui/")
    input("Нажмите Enter для выхода...")
    sys.exit(1)

# Внешние зависимости
try:
    from watchdog.observers import Observer
    from logging.handlers import RotatingFileHandler
except ImportError as e:
    print(f"❌ Ошибка импорта внешних зависимостей: {e}")
    print("Установите необходимые пакеты:")
    print("  pip install watchdog winotify pillow pystray")
    input("Нажмите Enter для выхода...")
    sys.exit(1)

# Глобальные переменные
logger = None
RUNNING = True

def setup_logging():
    """
    Настройка системы логирования с ротацией файлов.
    
    Returns:
        logging.Logger: Настроенный логгер
    """
    try:
        # Создаем директорию для логов
        LOG_DIR.mkdir(exist_ok=True)
        
        # Настройка обработчика с ротацией
        log_handler = RotatingFileHandler(
            LOG_DIR / 'file_watcher.log',
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        
        # Настройка форматирования
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        log_handler.setFormatter(formatter)
        
        # Основная настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            handlers=[log_handler]
        )
        
        logger = logging.getLogger(__name__)
        logger.info("=== Система логирования инициализирована ===")
        return logger
        
    except Exception as e:
        print(f"❌ Ошибка настройки логирования: {e}")
        # Создаем простой логгер если основной не работает
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)

def validate_configuration():
    """
    Проверяет корректность конфигурации системы.
    
    Returns:
        bool: True если конфигурация корректна
    """
    logger.info("Проверка конфигурации системы...")
    
    try:
        # Получаем пути для проверки
        paths_to_check = get_watch_paths()
        
        # Добавляем дополнительные пути
        from config.settings import DEST_BASE, ICON_PATH
        paths_to_check.extend([
            {'path': DEST_BASE, 'description': 'Базовая директория назначения'},
            {'path': Path(ICON_PATH).parent, 'description': 'Директория с иконкой'}
        ])
        
        # Проверяем пути
        all_valid = validate_paths(paths_to_check)
        
        if not all_valid:
            logger.warning("⚠️ Обнаружены проблемы в конфигурации, но работа продолжится")
        
        # Тестируем условия фильтрации
        test_filename_conditions(WATCH_CONFIGS)
        
        return True
        
    except Exception as e:
        logger.error(f"Критическая ошибка при проверке конфигурации: {e}")
        return False

def create_observers():
    """
    Создает и запускает наблюдателей файловой системы.
    
    Returns:
        list: Список кортежей (observer, config) активных наблюдателей
    """
    logger.info("Создание наблюдателей файловой системы...")
    observers = []
    
    for i, config in enumerate(WATCH_CONFIGS):
        try:
            path = config["watch_dir"]
            conditions = config["conditions"]
            description = config.get("description", f"Наблюдатель {i+1}")
            
            # Проверяем существование директории
            if not Path(path).exists():
                logger.warning(f"⚠️ Пропуск несуществующей директории: {path}")
                continue
            
            # Создаем обработчик и наблюдателя
            handler = MultiDirHandler(conditions)
            observer = Observer()
            observer.schedule(handler, path, recursive=True)
            observer.start()
            
            observers.append((observer, config))
            logger.info(f"✅ Запущен наблюдатель: {description} -> {path}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания наблюдателя для {config.get('watch_dir', 'неизвестная директория')}: {e}")
    
    logger.info(f"Создано {len(observers)} активных наблюдателей из {len(WATCH_CONFIGS)} возможных")
    return observers

def background_monitoring(observers):
    """
    Фоновый мониторинг состояния системы.
    
    Args:
        observers (list): Список наблюдателей для мониторинга
    """
    logger.info("Запуск фонового мониторинга системы...")
    
    from config.settings import HEARTBEAT_INTERVAL, HEALTH_CHECK_INTERVAL
    heartbeat_counter = 0
    
    try:
        while RUNNING:
            time.sleep(1)
            heartbeat_counter += 1
            
            # Проверка здоровья наблюдателей
            if heartbeat_counter % HEALTH_CHECK_INTERVAL == 0:
                monitor_observer_health(observers)
            
            # Общая проверка системы
            if heartbeat_counter % HEARTBEAT_INTERVAL == 0:
                daemon_heartbeat()
                heartbeat_counter = 0
                
                # Логируем статистику
                active_count = sum(1 for obs, _ in observers if obs.is_alive())
                logger.info(f"📊 Статистика: {active_count}/{len(observers)} наблюдателей активны")
    
    except KeyboardInterrupt:
        logger.info("Получен сигнал KeyboardInterrupt в фоновом мониторинге")
    except Exception as e:
        logger.error(f"Ошибка в фоновом мониторинге: {e}")
    finally:
        cleanup_observers(observers)

def cleanup_observers(observers):
    """
    Корректное завершение работы наблюдателей.
    
    Args:
        observers (list): Список наблюдателей для остановки
    """
    logger.info("Остановка наблюдателей файловой системы...")
    
    for i, (observer, config) in enumerate(observers):
        try:
            description = config.get('description', f'Наблюдатель {i+1}')
            observer.stop()
            observer.join(timeout=10)
            logger.info(f"✅ Остановлен: {description}")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при остановке наблюдателя {i+1}: {e}")
    
    logger.info("Все наблюдатели остановлены")

def signal_handler(signum, frame):
    """
    Обработчик системных сигналов для корректного завершения.
    
    Args:
        signum: Номер сигнала
        frame: Фрейм выполнения
    """
    global RUNNING
    logger.info(f"Получен сигнал {signum}, инициируется завершение работы...")
    RUNNING = False

def main():
    """
    Основная функция приложения.
    
    Returns:
        int: Код завершения программы
    """
    global logger, RUNNING
    
    try:
        # Инициализация системы
        logger = setup_logging()
        logger.info("🚀 === ЗАПУСК СИСТЕМЫ МОНИТОРИНГА ФАЙЛОВ STAT ===")
        logger.info(f"Базовая директория: {Path(__file__).parent}")
        
        # Установка обработчиков сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Проверка конфигурации
        if not validate_configuration():
            logger.error("❌ Критические ошибки конфигурации, завершение работы")
            show_error_notification("Критические ошибки конфигурации")
            return 1
        
        # Создание наблюдателей
        observers = create_observers()
        if not observers:
            logger.error("❌ Не удалось запустить ни одного наблюдателя")
            show_error_notification("Не удалось запустить наблюдателей")
            return 1
        
        # Настройка и запуск UI
        logger.info("Инициализация пользовательского интерфейса...")
        tray_app = TrayApp()
        tray_app.observers = observers
        
        if not tray_app.setup_tray():
            logger.warning("⚠️ Системный трей недоступен, работа продолжится без UI")
        
        # Запуск фонового мониторинга
        bg_thread = threading.Thread(
            target=background_monitoring, 
            args=(observers,), 
            daemon=True,
            name="BackgroundMonitoring"
        )
        bg_thread.start()
        
        logger.info(f"🎯 Система запущена успешно! Активных наблюдателей: {len(observers)}")
        
        # Показываем уведомление о запуске
        show_startup_notification()
        
        # Основной цикл приложения
        if tray_app.icon:
            logger.info("Запуск в режиме системного трея...")
            tray_app.run()  # Блокирующий вызов
        else:
            logger.info("Запуск в консольном режиме...")
            # Простой цикл ожидания если нет трея
            try:
                while RUNNING:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Получен Ctrl+C")
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения от пользователя")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        show_error_notification(f"Критическая ошибка: {str(e)}")
        return 1
    finally:
        logger.info("Завершение работы системы...")
        RUNNING = False
        if 'observers' in locals():
            cleanup_observers(observers)
        logger.info("=== СИСТЕМА ОСТАНОВЛЕНА ===")
        return 0

if __name__ == "__main__":
    sys.exit(main())
