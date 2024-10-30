from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel

class DocumentTag(SQLModel, table=True):
    document_id: Optional[int] = Field(
        default=None, foreign_key="document.id", primary_key=True
    )
    tag_id: Optional[int] = Field(
        default=None, foreign_key="tag.id", primary_key=True
    )

class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    
    # Relationships
    @property
    def documents_count(self) -> int:
        return len(self.documents)
    
    documents: List["Document"] = Relationship(back_populates="tags", link_model=DocumentTag)

class TagCreate(BaseModel):
    name: str
    description: Optional[str] = None

class TagUpdate(BaseModel):
    description: str

class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: Optional[str] = None
    content: str = Field(default="")  # This will be indexed with FTS5 later
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    tags: List["Tag"] = Relationship(back_populates="documents", link_model=DocumentTag)

class DocumentRead(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    content: str
    created_at: datetime
    updated_at: datetime
    tags: List[Tag] = []

    class Config:
        from_attributes = True

class DocumentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    content: str
    tag_ids: List[int] = Field(default_factory=list)
