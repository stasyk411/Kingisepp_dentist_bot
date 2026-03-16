"""
Версии миграций базы данных
"""

from .v001_initial import CreateInitialTables
from .v002_blocked_days import AddBlockedDaysTable
from .v003_working_hours import AddWorkingHoursTable
from .v004_temp_bookings import AddTempBookingsTable
from .v005_convert_to_utc import ConvertSlotsToUTC
from .v006_user_settings import AddUserSettingsTable  # ✅ НОВАЯ МИГРАЦИЯ

__all__ = [
    'CreateInitialTables', 
    'AddBlockedDaysTable', 
    'AddWorkingHoursTable',
    'AddTempBookingsTable',
    'ConvertSlotsToUTC',
    'AddUserSettingsTable'  # ✅ ДОБАВИЛИ В СПИСОК
]