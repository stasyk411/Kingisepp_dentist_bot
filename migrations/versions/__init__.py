"""
Версии миграций базы данных
"""

from .v001_initial import CreateInitialTables
from .v002_blocked_days import AddBlockedDaysTable
from .v003_working_hours import AddWorkingHoursTable
from .v004_temp_bookings import AddTempBookingsTable

__all__ = [
    'CreateInitialTables', 
    'AddBlockedDaysTable', 
    'AddWorkingHoursTable',
    'AddTempBookingsTable'
]