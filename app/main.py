from typing import Annotated, List
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlmodel import Session, SQLModel, create_engine, select, func
from .models import Tag, Document, TagCreate, TagUpdate, DocumentCreate, DocumentRead, DocumentTag, TagWithCount
from .config import get_settings

app = FastAPI(title="Markdown API")

# Database setup
settings = get_settings()
engine = create_engine(settings.database_url)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# Dependencies
SessionDep = Annotated[Session, Depends(get_session)]
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key != get_settings().api_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )
    return api_key

APIKeyDep = Annotated[str, Security(verify_api_key)]

# Startup event
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Tags endpoints
@app.get("/tags/", response_model=List[TagWithCount])
def list_tags(
    session: SessionDep,
    _: APIKeyDep
):
    """
    List all available tags with document counts.
    """
    # Subquery to count documents for each tag
    count_subquery = (
        select(DocumentTag.tag_id, func.count(DocumentTag.document_id).label("documents_count"))
        .group_by(DocumentTag.tag_id)
        .subquery()
    )

    # Join the tags with their document counts
    tags_with_counts = (
        select(Tag, count_subquery.c.documents_count)
        .join(count_subquery, Tag.id == count_subquery.c.tag_id, isouter=True)
    )

    # Execute the query and map the results
    results = session.exec(tags_with_counts).all()
    tags = [TagWithCount(**tag.model_dump(), documents_count=count or 0) for tag, count in results]
    return tags

@app.patch("/tags/{tag_id}", response_model=Tag)
def update_tag_description(
    tag_id: int,
    tag_data: TagUpdate,
    session: SessionDep,
    _: APIKeyDep
):
    """
    Update a tag's description
    """
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    tag.description = tag_data.description
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag

@app.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: int,
    session: SessionDep,
    _: APIKeyDep
):
    """
    Get a document by ID including its tags
    """
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@app.post("/documents/", response_model=DocumentRead, status_code=201)
def create_document(
    document_data: DocumentCreate,
    session: SessionDep,
    _: APIKeyDep
):
    """
    Create a new document with optional tags
    """
    # First verify all tags exist
    if document_data.tag_ids:
        tags = session.exec(
            select(Tag).where(Tag.id.in_(document_data.tag_ids))
        ).all()
        if len(tags) != len(document_data.tag_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more tag IDs do not exist"
            )
    else:
        tags = []

    # Create the document
    document = Document(
        title=document_data.title,
        description=document_data.description,
        content=document_data.content,
        tags=tags
    )
    
    session.add(document)
    session.commit()
    session.refresh(document)
    return document

@app.post("/tags/", response_model=Tag, status_code=201)
def create_tag(
    tag_data: TagCreate,
    session: SessionDep,
    _: APIKeyDep
):
    """
    Create a new tag
    """
    tag = Tag(name=tag_data.name, description=tag_data.description)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag
