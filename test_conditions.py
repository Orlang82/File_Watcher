from core.utils import create_flexible_condition, normalize_filename_for_comparison
import logging
from pathlib import Path
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                   format='%(message)s')

def test_real_files(watch_configs):
    """
    Тестирует условия фильтрации на реальных файлах.
    """
    logger = logging.getLogger(__name__)
    logger.info("=== Тестирование условий фильтрации файлов ===")
    
    for config in watch_configs:
        watch_dir = Path(config["watch_dir"])
        conditions = config["conditions"]
        
        if not watch_dir.exists():
            logger.error(f"\nДиректория не существует: {watch_dir}")
            continue
            
        logger.info(f"\nДиректория: {watch_dir}")
        
        # Получаем список реальных файлов
        real_files = [f.name for f in watch_dir.iterdir() if f.is_file()]
        
        matching_files = []
        for filename in real_files:
            normalized = normalize_filename_for_comparison(filename)
            logger.debug(f"Проверка файла:")
            logger.debug(f"  Оригинал: '{filename}'")
            logger.debug(f"  Нормализован: '{normalized}'")
            
            # Используем нормализованное имя для проверки условий
            if any(cond(normalized) for cond in conditions):
                matching_files.append(filename)
        
        if matching_files:
            logger.info("Подходящие файлы:")
            for file in matching_files:
                logger.info(f"  {file}")
        else:
            logger.info("  Подходящих файлов не найдено")
    
    logger.info("=== Конец тестирования ===\n")

# Создаем тестовую конфигурацию
test_configs = [
    {
        "watch_dir": r"r:\Подразделения\РИСК-менеджмент\Внутренние\3 - РИСК ЛИКВИДНОСТИ\1 - БАЛАНС\15-08-2025",
        "conditions": [
            # Форма 01X и нормативы
            lambda name: normalize_filename_for_comparison(name).startswith("01x") and name.endswith(".xlsx"),
            lambda name: normalize_filename_for_comparison(name).startswith(("норм", "norm")),
            
            # Форма C5
            create_flexible_condition(["c5", "с5"]),
            
            # Форма 6RX
            create_flexible_condition(["6rx", "6рх"]),
            # Проверка файлов "залишки на рах вкл" по пятницам
            lambda name: (
                datetime.now().weekday() == 4  # 4 = пятница
                and any(x in normalize_filename_for_comparison(name) 
                     for x in ("залишки на рах вкл", "zalishki na rax vkl"))
            ),
        
            # Форма 6JX и активы
            create_flexible_condition(["6jx", "6јх"]),
            lambda name: (
                print(f"Проверка 'активи' для '{name}'\n"
                      f"Нормализовано: '{normalize_filename_for_comparison(name)}'\n"
                      f"Содержит 'активи': {'активи' in normalize_filename_for_comparison(name)}\n"
                      f"Содержит 'aktivi': {'aktivi' in normalize_filename_for_comparison(name)}") or 
                any(x in normalize_filename_for_comparison(name) for x in ("активи", "aktivi"))
            ),
            
            # Форма 6KX и SR файлы
            create_flexible_condition(["6kx", "6кх"]),
            lambda name: normalize_filename_for_comparison(name).startswith("sr"),
            
            # Форма 42X
            create_flexible_condition(["42x"])
        ]
    }
]

# Запускаем тестирование
if __name__ == "__main__":
    test_real_files(test_configs)