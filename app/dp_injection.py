from typing import Optional

from pydantic import BaseModel, Field


class ClassParams:
    def __init__(self, q: Optional[str] = None, offset: int = 0, limit: int = 100):
        self.q = q
        self.offset = offset
        self.limit = limit


class PydanticParams(BaseModel):
    q: Optional[str] = Field(None, min_length=2)
    offset: int = Field(0, ge=0)
    limit: int = Field(100, gt=0)
