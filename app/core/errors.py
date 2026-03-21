class AppError(Exception):
    """Base application error."""


class NotFoundError(AppError):
    """Entity was not found."""


class ValidationError(AppError):
    """Domain validation failed."""

