from PySide6.QtCore import QSettings
from typing import Any, List, Optional, Dict, Union


class Settings:
    """Wrapper for QSettings to handle lists and other data types"""

    def __init__(self):
        from ..config import APP_NAME, APP_ORGANIZATION
        self.settings = QSettings(APP_ORGANIZATION, APP_NAME)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from settings"""
        value = self.settings.value(key, default)

        # Convert string booleans back to bool
        if isinstance(value, str):
            if value.lower() == 'true':
                return True
            elif value.lower() == 'false':
                return False

        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """Save a value to settings"""
        self.settings.setValue(key, value)

    def get_list(self, key: str, default: Optional[List] = None) -> List:
        """Get a list from settings"""
        value = self.settings.value(key, default or [])
        if isinstance(value, str):
            # Handle single string value
            return [value] if value else []
        return value if isinstance(value, list) else []

    def contains(self, key: str) -> bool:
        """Check if a key exists in settings"""
        return self.settings.contains(key)

    def remove(self, key: str) -> None:
        """Remove a key from settings"""
        self.settings.remove(key)

    def clear(self) -> None:
        """Clear all settings"""
        self.settings.clear()

    def sync(self) -> None:
        """Force settings to be written to storage"""
        self.settings.sync()
