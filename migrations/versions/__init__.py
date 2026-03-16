"""
Версии миграций базы данных
"""

from .v001_initial import CreateInitialTables
from .v002_blocked_days import AddBlockedDaysTable
from .v003_working_hours import AddWorkingHoursTable
from .v004_temp_bookings import AddTempBookingsTable
from .v006_user_settings import AddUserSettingsTable

__all__ = [
    'CreateInitialTables', 
    'AddBlockedDaysTable', 
    'AddWorkingHoursTable',
    'AddTempBookingsTable',
    'AddUserSettingsTable'
]