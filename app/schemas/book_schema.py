from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import List
import datetime

class Genre(str, Enum):
    Fiction = "Fiction"
    Non_Fiction = "Non-Fiction"
    Science = "Science"
    History = "History"

class SortField(str, Enum):
    title = "title"
    published_year = "published_year"

class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"

class BookBase(BaseModel):
    title: str = Field(..., min_length=1)
    genre: Genre
    published_year: int = Field(..., ge=1800, le=datetime.datetime.now().year)

    @field_validator("title")
    def not_blank(self, v):
        if not v or not v.strip():
            raise ValueError("title must not be empty")
        return v

class BookCreate(BookBase):
    authors: List[str] = Field(min_items=1)

class BookUpdate(BaseModel):
    title: str | None
    genre: Genre | None
    published_year: int | None
    authors: List[str] | None

class BookOut(BookBase):
    id: int
    authors: List[str]

    class Config:
        orm_mode = True

class MessageResponse(BaseModel):
    message: str
