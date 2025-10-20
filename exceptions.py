# Custom exceptions for the email service
class EmailRateLimitException(Exception):
    """Exception raised when email sending rate limit is exceeded."""
    pass

class EmailSendException(Exception):
    """Exception raised when email sending fails."""
    pass

class DatabaseException(Exception):
    """Exception raised for database related errors."""
    pass
