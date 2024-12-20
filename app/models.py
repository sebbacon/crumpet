from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel


class DocumentTag(SQLModel, table=True):
    document_id: Optional[int] = Field(
        default=None, foreign_key="document.id", primary_key=True
    )
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id", primary_key=True)


class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None

    # Relationships
    documents: List["Document"] = Relationship(
        back_populates="tags", link_model=DocumentTag
    )

    def __str__(self):
        return self.name

    class Config:
        arbitrary_types_allowed = True  # Allow complex types for relationships


class TagWithCount(SQLModel):
    id: int
    name: str
    description: Optional[str]
    documents_count: int = 0  # Additional field for document count

    class Config:
        arbitrary_types_allowed = True


class TagCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TagUpdate(BaseModel):
    description: str


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: Optional[str] = None
    content: str = Field(default="")
    interestingness: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    tags: List["Tag"] = Relationship(back_populates="documents", link_model=DocumentTag)


class DocumentRead(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    content: str
    interestingness: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    tags: List[Tag] = []

    class Config:
        from_attributes = True


class DocumentSearchResult(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    interestingness: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    tags: List[Tag] = []

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    total: int
    results: List[DocumentSearchResult]


class DocumentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    content: str
    interestingness: Optional[int] = Field(default=None, ge=0, le=2)
    tag_ids: List[int] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentAddTags(BaseModel):
    tag_ids: List[int]
