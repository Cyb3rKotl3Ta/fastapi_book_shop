from pydantic import BaseModel
from typing import Optional

class Message(BaseModel):
    message: str

class PaginationParams(BaseModel):
    skip: int = 0
    limit: int = 100