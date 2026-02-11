"""Custom exceptions for Confluence operations."""


class ConfluenceError(Exception):
    """Base exception for Confluence operations"""
    pass


class ApiError(ConfluenceError):
    """Exception for API-related errors"""
    pass


class FileError(ConfluenceError):
    """Exception for file operation errors"""
    pass


class TranslationError(ConfluenceError):
    """Exception for translation-related errors"""
    pass
