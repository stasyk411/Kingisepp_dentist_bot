"""
Запуск миграций при старте приложения
"""

import aiosqlite
from .migration_manager import MigrationManager
from .versions import *

async def run_migrations(db_path: str) -> None:
    """Запустить все миграции"""
    manager = MigrationManager(db_path)
    
    # Регистрируем все миграции
    manager.register(CreateInitialTables())
    manager.register(AddBlockedDaysTable())
    manager.register(AddWorkingHoursTable())
    manager.register(AddTempBookingsTable())
    
    # Применяем миграции
    await manager.migrate()