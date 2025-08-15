"""
Правила мониторинга директорий и условия отбора файлов
"""

from core.utils import normalize_filename_for_comparison, create_flexible_condition
from datetime import datetime

# Конфигурация директорий для наблюдения и условий отбора файлов
WATCH_CONFIGS = [
    {
        "watch_dir": r"q:\STAT\new_stat\STA_ARCH\ARX_F01\2025", 
        "description": "Форма 01X и нормативы",
        "conditions": [
            lambda name: normalize_filename_for_comparison(name).startswith("01x") and name.endswith(".xlsx"), 
            lambda name: normalize_filename_for_comparison(name).startswith(("норм", "norm"))
        ]
    },
    {
        "watch_dir": r"q:\STAT\new_stat\STA_ARCH\ARX_FC5\2025", 
        "description": "Форма C5",
        "conditions": [
            create_flexible_condition(["c5", "с5"])
        ]
    },
    {
        "watch_dir": r"q:\STAT\new_stat\STA_ARCH\ARX_6RX\2025", 
        "description": "Форма 6RX",
        "conditions": [
            create_flexible_condition(["6rx", "6рх"]),
            # Проверка файлов "залишки на рах вкл" по пятницам
            lambda name: (
                datetime.now().weekday() == 4  # 4 = пятница
                and any(x in normalize_filename_for_comparison(name) 
                     for x in ("залишки на рах вкл", "zalishki na rax vkl"))
            )
        ]
    },
    {
        "watch_dir": r"q:\STAT\new_stat\STA_ARCH\ARX_6JX\2025",
        "description": "Форма 6JX и активы",
        "conditions": [
            create_flexible_condition(["6jx", "6јх"]),
            lambda name: normalize_filename_for_comparison(name).startswith(("активи", "aktivi"))
        ]
    },
    {
        "watch_dir": r"q:\STAT\new_stat\STA_ARCH\ARX_F6KX\2025", 
        "description": "Форма 6KX и SR файлы",
        "conditions": [
            create_flexible_condition(["6kx", "6кх"]),
            lambda name: normalize_filename_for_comparison(name).startswith("sr")
        ]
    },
    {
        "watch_dir": r"q:\STAT\new_stat\STA_ARCH\ARX_F42\2025",
        "description": "Форма 42X",
        "conditions": [
            create_flexible_condition(["42x"])
        ]
    }
]

def get_watch_paths():
    """
    Возвращает список всех путей для мониторинга.
    
    Returns:
        list: Список путей для проверки существования
    """
    return [
        {
            'path': config['watch_dir'],
            'description': f"Директория мониторинга: {config['description']}"
        }
        for config in WATCH_CONFIGS
    ]

def get_conditions_for_path(watch_dir):
    """
    Возвращает условия фильтрации для указанной директории.
    
    Args:
        watch_dir (str): Путь к директории
        
    Returns:
        list: Список функций-условий или None если директория не найдена
    """
    for config in WATCH_CONFIGS:
        if config['watch_dir'] == watch_dir:
            return config['conditions']
    return None

def get_description_for_path(watch_dir):
    """
    Возвращает описание для указанной директории.
    
    Args:
        watch_dir (str): Путь к директории
        
    Returns:
        str: Описание директории или None если не найдено
    """
    for config in WATCH_CONFIGS:
        if config['watch_dir'] == watch_dir:
            return config['description']
    return None
