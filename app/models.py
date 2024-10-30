from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    documents_count: int = Field(default=0)

class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: Optional[str] = None
    body: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
