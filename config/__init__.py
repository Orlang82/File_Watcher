#Модуль конфигурации для файлового мониторинга

from .settings import *
from .watch_rules import WATCH_CONFIGS

__all__ = [
    'BASE_DIR', 'LOG_DIR', 'DEST_BASE', 'ICON_PATH',
    'COPY_DELAY', 'STABILITY_CHECK_INTERVAL', 'MAX_COPY_ATTEMPTS',
    'WATCH_CONFIGS', 'RUNNING'
]
