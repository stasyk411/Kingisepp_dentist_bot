"""
Менеджер миграций базы данных
"""

import aiosqlite
from typing import List, Dict, Any
from datetime import datetime

class Migration:
    """Базовый класс миграции"""
    
    def __init__(self, version: str, description: str):
        self.version = version
        self.description = description
        self.created_at = datetime.now()
    
    async def up(self, db: aiosqlite.Connection) -> None:
        """Применить миграцию"""
        raise NotImplementedError("Метод up() должен быть реализован")
    
    async def down(self, db: aiosqlite.Connection) -> None:
        """Откатить миграцию"""
        raise NotImplementedError("Метод down() должен быть реализован")

class MigrationManager:
    """Управляет миграциями БД"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations: List[Migration] = []
    
    def register(self, migration: Migration) -> None:
        """Зарегистрировать миграцию"""
        self.migrations.append(migration)
        # Сортируем по версии
        self.migrations.sort(key=lambda m: m.version)
    
    async def init_schema_table(self) -> None:
        """Создать таблицу для отслеживания миграций"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    description TEXT,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    
    async def get_applied_migrations(self) -> List[str]:
        """Получить список примененных миграций"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT version FROM schema_migrations ORDER BY version")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    
    async def apply_migration(self, migration: Migration) -> None:
        """Применить одну миграцию"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("BEGIN TRANSACTION")
                
                # Применяем миграцию
                await migration.up(db)
                
                # Записываем в историю
                await db.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                    (migration.version, migration.description)
                )
                
                await db.commit()
                print(f"✅ Применена миграция {migration.version}: {migration.description}")
                
            except Exception as e:
                await db.rollback()
                print(f"❌ Ошибка при применении миграции {migration.version}: {e}")
                raise
    
    async def rollback_migration(self, migration: Migration) -> None:
        """Откатить одну миграцию"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("BEGIN TRANSACTION")
                
                # Откатываем миграцию
                await migration.down(db)
                
                # Удаляем из истории
                await db.execute(
                    "DELETE FROM schema_migrations WHERE version = ?",
                    (migration.version,)
                )
                
                await db.commit()
                print(f"↩️ Отменена миграция {migration.version}: {migration.description}")
                
            except Exception as e:
                await db.rollback()
                print(f"❌ Ошибка при откате миграции {migration.version}: {e}")
                raise
    
    async def migrate(self) -> None:
        """Применить все новые миграции"""
        await self.init_schema_table()
        
        applied = await self.get_applied_migrations()
        
        for migration in self.migrations:
            if migration.version not in applied:
                await self.apply_migration(migration)
            else:
                print(f"⏭️ Пропуск миграции {migration.version} (уже применена)")
