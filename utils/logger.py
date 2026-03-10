"""
Единый структурированный логгер для бота
Заменяет все print() на информативное логирование с контекстом
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

class BotLogger:
    """Структурированный логгер с контекстом"""
    
    @staticmethod
    def _format_message(message: str, user_id: Optional[int] = None, **context) -> str:
        """Форматирует сообщение с контекстом"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        parts = [f"[{timestamp}] {message}"]
        
        if user_id:
            parts.append(f"user_id={user_id}")
        
        # Добавляем остальные контекстные данные
        for key, value in context.items():
            parts.append(f"{key}={value}")
        
        return " | ".join(parts)
    
    @staticmethod
    def info(message: str, user_id: Optional[int] = None, **context):
        """INFO уровень с контекстом"""
        formatted = BotLogger._format_message(message, user_id, **context)
        logging.info(formatted)
    
    @staticmethod
    def warning(message: str, user_id: Optional[int] = None, **context):
        """WARNING уровень с контекстом"""
        formatted = BotLogger._format_message(f"⚠️ {message}", user_id, **context)
        logging.warning(formatted)
    
    @staticmethod
    def error(message: str, user_id: Optional[int] = None, **context):
        """ERROR уровень с контекстом"""
        formatted = BotLogger._format_message(f"❌ {message}", user_id, **context)
        logging.error(formatted)
    
    @staticmethod
    def critical(message: str, user_id: Optional[int] = None, **context):
        """CRITICAL уровень с контекстом"""
        formatted = BotLogger._format_message(f"🚨 {message}", user_id, **context)
        logging.critical(formatted)
    
    @staticmethod
    def success(message: str, user_id: Optional[int] = None, **context):
        """SUCCESS уровень с контекстом"""
        formatted = BotLogger._format_message(f"✅ {message}", user_id, **context)
        logging.info(formatted)
    
    @staticmethod
    def debug(message: str, user_id: Optional[int] = None, **context):
        """DEBUG уровень с контекстом"""
        formatted = BotLogger._format_message(f"🔍 {message}", user_id, **context)
        logging.debug(formatted)

# Глобальный экземпляр для удобного импорта
logger = BotLogger()
