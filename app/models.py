from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel

class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    documents_count: int = Field(default=0)

class TagCreate(BaseModel):
    name: str
    description: Optional[str] = None

class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: Optional[str] = None
    body: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
