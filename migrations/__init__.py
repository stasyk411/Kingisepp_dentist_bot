"""
Система миграций базы данных
Обеспечивает безопасные обновления схемы БД в продакшене
"""

from .migration_manager import MigrationManager
from .runner import run_migrations

__all__ = ['MigrationManager', 'run_migrations']
