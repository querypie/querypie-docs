"""File I/O operations for Confluence data."""

import logging
import os
from typing import Dict, Optional, Any, Protocol

import yaml

from fetch.exceptions import FileError


class FileManagerProtocol(Protocol):
    """Protocol for file operations"""

    def save_file(self, filepath: str, content: Any, is_binary: bool = False) -> bool:
        ...

    def save_yaml(self, filepath: str, data: Any) -> bool:
        ...

    def load_yaml(self, filepath: str) -> Optional[Dict]:
        ...

    def ensure_directory(self, directory: str) -> bool:
        ...


class FileManager:
    """Handles all file I/O operations"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def ensure_directory(self, directory: str) -> bool:
        """Ensure directory exists"""
        try:
            os.makedirs(directory, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Error creating directory {directory}: {str(e)}")
            raise FileError(f"Failed to create directory: {str(e)}")

    def save_file(self, filepath: str, content: Any, is_binary: bool = False) -> bool:
        """Save content to file"""
        try:
            self.ensure_directory(os.path.dirname(filepath))
            mode = 'wb' if is_binary else 'w'
            encoding = None if is_binary else 'utf-8'

            with open(filepath, mode, encoding=encoding) as f:
                f.write(content)

            self.logger.debug(f"Saved {len(content)} bytes to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving file {filepath}: {str(e)}")
            raise FileError(f"Failed to save file: {str(e)}")

    def save_yaml(self, filepath: str, data: Any) -> bool:
        """Save YAML data to a file with quoted strings"""
        return self.save_file(filepath, yaml.dump(data, allow_unicode=True, sort_keys=False, default_style='"'))

    def load_yaml(self, filepath: str) -> Optional[Dict]:
        """Read YAML from a file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Error loading YAML from {filepath}: {str(e)}")
            raise FileError(f"Failed to load YAML: {str(e)}")
        return None
