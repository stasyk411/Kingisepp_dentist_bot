"""
v006 - Таблица настроек пользователей (часовой пояс)
"""

class AddUserSettingsTable:
    def __init__(self):
        self.version = "006"
        self.description = "Добавление таблицы user_settings для хранения часового пояса"
    
    async def up(self, db):
        # 1. Создаём таблицу user_settings
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                utc_offset INTEGER DEFAULT 3,  -- По умолчанию Москва (+3)
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES patients(id) ON DELETE CASCADE
            )
        """)
        
        # 2. Индекс для быстрых запросов
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_settings_updated 
            ON user_settings(updated_at)
        """)
        
        # 3. Для всех существующих пациентов создаём записи с дефолтным +3
        await db.execute("""
            INSERT OR IGNORE INTO user_settings (user_id, utc_offset)
            SELECT id, 3 FROM patients
        """)
        
        print("✅ Таблица user_settings создана")
    
    async def down(self, db):
        # Откат: удаляем таблицу
        await db.execute("DROP TABLE IF EXISTS user_settings")
        print("⏪ Таблица user_settings удалена")