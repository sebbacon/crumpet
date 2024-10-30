from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentCreate(BaseModel):
    title: str
    description: str
    content: str
    tags: Optional[str] = None

class Document(DocumentCreate):
    id: int
    created_at: datetime
    updated_at: datetime
