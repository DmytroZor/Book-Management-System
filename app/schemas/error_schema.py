from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, Any

class ErrorResponse(BaseModel):
    detail: str
    message: Optional[str]
    details: Optional[Any]


ErrorResponse.model_rebuild()
