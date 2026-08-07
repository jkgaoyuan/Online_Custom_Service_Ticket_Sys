class TicketSystemException(Exception):
    """Base exception for ticket system."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(TicketSystemException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class PermissionDeniedException(TicketSystemException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403)


class DuplicateException(TicketSystemException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status_code=409)
