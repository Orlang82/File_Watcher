"""
Утилиты для работы с именами файлов и условиями фильтрации
"""

import logging

logger = logging.getLogger(__name__)

def normalize_filename_for_comparison(filename):
    """
    Нормализует имя файла для сравнения, заменяя похожие кириллические 
    и латинские символы на единый вариант.
    
    Args:
        filename (str): Исходное имя файла
        
    Returns:
        str: Нормализованное имя файла в нижнем регистре
    """
    # Расширенный словарь замен
    replacements = {
        'а': 'a', 'А': 'A',
        'е': 'e', 'Е': 'E', 
        'к': 'k', 'К': 'K',
        'м': 'm', 'М': 'M',
        'н': 'n', 'Н': 'N',
        'о': 'o', 'О': 'O',
        'р': 'r', 'Р': 'R',
        'с': 'c', 'С': 'C',
        'т': 't', 'Т': 'T',
        'у': 'u', 'У': 'U',
        'х': 'x', 'Х': 'X',
        'ј': 'j',  # Сербская ј
        'и': 'i',  # Добавляем и -> i
        'і': 'i',  # Добавляем і -> i
        'в': 'v',  # Добавляем в -> v
        'л': 'l',  # Добавляем л -> l
        'ф': 'f',  # Добавляем ф -> f
        'д': 'd',  # Добавляем д -> d
        'ш': 'sh',  # Добавляем ш -> sh
        'з': 'z',   # Добавляем з -> z
    }
    
    result = filename.lower()
    for cyr, lat in replacements.items():
        result = result.replace(cyr, lat.lower())
    
    logger.debug(f"Нормализация '{filename}' -> '{result}'")
    return result

def create_flexible_condition(patterns):
    """
    Создает условие, которое работает с различными вариантами 
    кириллицы/латиницы в именах файлов.
    
    Args:
        patterns (list): Список шаблонов для поиска
        
    Returns:
        function: Функция-условие для проверки имени файла
    """
    def condition(filename):
        normalized = normalize_filename_for_comparison(filename)
        result = any(normalized.startswith(pattern.lower()) for pattern in patterns)
        if result:
            logger.debug(f"Файл '{filename}' соответствует шаблонам {patterns}")
        return result
    
    return condition

def test_filename_conditions(watch_configs):
    """
    Тестирует условия фильтрации на примерах файлов.
    
    Args:
        watch_configs (list): Список конфигураций для тестирования
    """
    test_files = [
        "6КХ_13082025.xlsx",
        "6КХ_данi_13082025.xlsx", 
        "sr_13082025.TXT",
        "6kx_test.xlsx",
        "С5_13082025.xlsx",
        "c5_test.xlsx",
        "01X_13082025.xlsx",
        "нормативы_13082025.xlsx",
        "6RX_13082025.xlsx",
        "6рх_test.xlsx",
        "активи вкл до файлу_13082025.xlsx",
        "6JX_13082025.xlsx",
        "42x_test.xlsx"
    ]
    
    logger.info("=== Тестирование условий фильтрации файлов ===")
    
    for config in watch_configs:
        watch_dir = config["watch_dir"]
        conditions = config["conditions"]
        logger.info(f"\nДиректория: {watch_dir}")
        
        matching_files = []
        for test_file in test_files:
            if any(cond(test_file.lower()) for cond in conditions):
                matching_files.append(test_file)
        
        if matching_files:
            logger.info(f"  Подходящие файлы: {', '.join(matching_files)}")
        else:
            logger.info("  Подходящих файлов не найдено")
    
    logger.info("=== Конец тестирования ===\n")

def validate_paths(paths_to_check):
    """
    Проверяет существование всех путей из конфигурации.
    
    Args:
        paths_to_check (list): Список путей для проверки
        
    Returns:
        bool: True если все пути существуют, False если есть проблемы
    """
    from pathlib import Path
    
    logger.info("Проверка существования директорий...")
    all_paths_valid = True
    
    for path_info in paths_to_check:
        if isinstance(path_info, dict):
            path = Path(path_info.get('path', ''))
            description = path_info.get('description', 'Неизвестный путь')
        else:
            path = Path(path_info)
            description = f"Путь: {path_info}"
        
        if not path.exists():
            logger.warning(f"❌ {description} не существует: {path}")
            all_paths_valid = False
        else:
            logger.info(f"✓ {description} найден: {path}")
    
    return all_paths_valid
