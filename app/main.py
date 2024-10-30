from typing import Annotated, List
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlmodel import Session, SQLModel, create_engine, select
from .models import Tag, Document, TagCreate, TagUpdate, DocumentCreate, DocumentRead
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
@app.get("/tags/", response_model=List[Tag])
def list_tags(
    session: SessionDep,
    _: APIKeyDep
):
    """
    List all available tags
    """
    tags = session.exec(select(Tag)).all()
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
    
    # Update tags count
    for tag in tags:
        tag.documents_count += 1
        session.add(tag)

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
