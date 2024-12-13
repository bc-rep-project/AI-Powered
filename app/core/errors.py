from fastapi import HTTPException, status
from typing import Dict, Any

class APIError(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = None,
        metadata: Dict[str, Any] = None
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "message": detail,
                "error_code": error_code or "UNKNOWN_ERROR",
                "metadata": metadata or {}
            }
        )

class AuthenticationError(APIError):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class AuthorizationError(APIError):
    def __init__(self, detail: str = "Not authorized"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class ValidationError(APIError):
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

class NotFoundError(APIError):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with id {resource_id} not found",
            error_code="RESOURCE_NOT_FOUND",
            metadata={"resource": resource, "id": resource_id}
        ) 