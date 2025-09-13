from fastapi import status

class AppError(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: int | str):
        super().__init__(
            message=f"{resource} with id={resource_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class UnauthorizedError(AppError):
    def __init__(self):
        super().__init__(
            message="Unauthorized: invalid or expired token",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class ForbiddenError(AppError):
    def __init__(self):
        super().__init__(
            message="Forbidden: insufficient permissions",
            status_code=status.HTTP_403_FORBIDDEN
        )
