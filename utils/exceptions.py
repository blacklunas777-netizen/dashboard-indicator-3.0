class AppException(Exception):
    """Base application exception."""
    pass

class DataFetchError(AppException):
    """Exception for data fetching errors."""
    pass

class ValidationError(AppException):
    """Exception for input validation errors."""
    pass
