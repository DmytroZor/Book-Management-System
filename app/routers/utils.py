from typing import Dict, Any

def get_common_responses() -> Dict[int, Dict[str, Any]]:
    from app.schemas.error_schema import ErrorResponse

    return {
        400: {"model": ErrorResponse, "description": "Bad Request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    }
