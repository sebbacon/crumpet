from typing import Annotated, List
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Security, Query
from fastapi.security.api_key import APIKeyHeader
from contextlib import asynccontextmanager
from sqlmodel import Session, SQLModel, create_engine, select, func
from sqlalchemy import text

from .models import (
    Tag,
    Document,
    TagCreate,
    TagUpdate,
    DocumentCreate,
    DocumentRead,
    DocumentTag,
    TagWithCount,
    DocumentAddTags,
)
from .config import get_settings


# Load API description from markdown file
description_path = Path(__file__).parent.parent / "DESCRIPTION.md"
with open(description_path, "r") as f:
    description = f.read()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event
    create_db_and_tables()  # Ensure this runs on app startup
    yield  # Run app


servers = [{"url": "https://crumpet.bacon.boutique", "description": "Main server"}]

app = FastAPI(
    title="Crumpet API", description=description, lifespan=lifespan, servers=servers
)

# Database setup
settings = get_settings()
engine = create_engine(settings.database_url)


def create_db_and_tables(db_engine=engine):
    # Create regular tables
    SQLModel.metadata.create_all(db_engine)

    # Create FTS5 virtual table
    with Session(db_engine) as session:
        session.exec(
            text(
                """
            CREATE VIRTUAL TABLE IF NOT EXISTS documentfts 
            USING fts5(
                title, 
                description, 
                content,
                tag_data,
                interestingness
            )
        """
            )
        )

        # Create triggers to keep FTS index updated
        session.exec(
            text(
                """
            CREATE TRIGGER IF NOT EXISTS document_ai AFTER INSERT ON document BEGIN
                INSERT INTO documentfts(rowid, title, description, content, tag_data, interestingness)
                VALUES (
                    new.id, 
                    new.title, 
                    COALESCE(new.description, ''),
                    new.content, 
                    COALESCE(
                        (
                            SELECT GROUP_CONCAT(t.name || ' ' || COALESCE(t.description, ''), ' ')
                            FROM tag t
                            JOIN documenttag dt ON dt.tag_id = t.id
                            WHERE dt.document_id = new.id
                        ),
                        ''
                    ),
                    CAST(new.interestingness AS TEXT)
                );
            END;
        """
            )
        )

        session.exec(
            text(
                """
            CREATE TRIGGER IF NOT EXISTS document_ad AFTER DELETE ON document BEGIN
                DELETE FROM documentfts WHERE rowid = old.id;
            END;
        """
            )
        )

        session.exec(
            text(
                """
            CREATE TRIGGER IF NOT EXISTS document_au AFTER UPDATE ON document BEGIN
                DELETE FROM documentfts WHERE rowid = old.id;
                INSERT INTO documentfts(rowid, title, description, content, tag_data, interestingness)
                VALUES (
                    new.id, 
                    new.title, 
                    COALESCE(new.description, ''),
                    new.content, 
                    COALESCE(
                        (
                            SELECT GROUP_CONCAT(t.name || ' ' || COALESCE(t.description, ''), ' ')
                            FROM tag t
                            JOIN documenttag dt ON dt.tag_id = t.id
                            WHERE dt.document_id = new.id
                        ),
                        ''
                    ),
                    CAST(new.interestingness AS TEXT)
                );
            END;
        """
            )
        )

        session.exec(
            text(
                """
            CREATE TRIGGER IF NOT EXISTS documenttag_ai AFTER INSERT ON documenttag BEGIN
                UPDATE documentfts 
                SET tag_data = COALESCE(
                    (
                        SELECT GROUP_CONCAT(t.name || ' ' || COALESCE(t.description, ''), ' ')
                        FROM tag t
                        JOIN documenttag dt ON dt.tag_id = t.id
                        WHERE dt.document_id = new.document_id
                    ),
                    ''
                )
                WHERE rowid = new.document_id;
            END;
        """
            )
        )

        session.exec(
            text(
                """
            CREATE TRIGGER IF NOT EXISTS documenttag_ad AFTER DELETE ON documenttag BEGIN
                UPDATE documentfts 
                SET tag_data = COALESCE(
                    (
                        SELECT GROUP_CONCAT(t.name || ' ' || COALESCE(t.description, ''), ' ')
                        FROM tag t
                        JOIN documenttag dt ON dt.tag_id = t.id
                        WHERE dt.document_id = old.document_id
                    ),
                    ''
                )
                WHERE rowid = old.document_id;
            END;
        """
            )
        )
        session.commit()


def get_session():
    with Session(engine) as session:
        yield session


# Dependencies
SessionDep = Annotated[Session, Depends(get_session)]
api_key_header = APIKeyHeader(name="X-API-Key")


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key != get_settings().api_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key


APIKeyDep = Annotated[str, Security(verify_api_key)]


# Tags endpoints
@app.get("/tags/", response_model=List[TagWithCount])
def list_tags(session: SessionDep, _: APIKeyDep):
    """
    List all available tags with document counts.
    """
    # Subquery to count documents for each tag
    count_subquery = (
        select(
            DocumentTag.tag_id,
            func.count(DocumentTag.document_id).label("documents_count"),
        )
        .group_by(DocumentTag.tag_id)
        .subquery()
    )

    # Join the tags with their document counts
    tags_with_counts = select(Tag, count_subquery.c.documents_count).join(
        count_subquery, Tag.id == count_subquery.c.tag_id, isouter=True
    )

    # Execute the query and map the results
    results = session.exec(tags_with_counts).all()
    tags = [
        TagWithCount(**tag.model_dump(), documents_count=count or 0)
        for tag, count in results
    ]
    return tags


@app.patch("/tags/{tag_id}", response_model=Tag)
def update_tag_description(
    tag_id: int, tag_data: TagUpdate, session: SessionDep, _: APIKeyDep
):
    """
    Update an existing tag's description
    """
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    tag.description = tag_data.description
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


@app.get("/documents/search", response_model=List[DocumentRead])
def search_documents(
    session: SessionDep,
    _: APIKeyDep,
    q: str = Query(..., min_length=3),
    min_interestingness: int = Query(None, ge=0, le=2),
):
    """
    Search documents using FTS5
    """
    # Build the FTS query
    query = "SELECT rowid FROM documentfts WHERE documentfts MATCH :query"
    params = {"query": q}

    if min_interestingness is not None:
        query += " AND CAST(interestingness AS INTEGER) >= :min_interestingness"
        params["min_interestingness"] = min_interestingness

    matching_docs = session.exec(text(query).params(**params)).all()

    # Then fetch complete Document objects for those IDs
    result = session.exec(
        select(Document).where(Document.id.in_([doc[0] for doc in matching_docs]))
    )
    documents = [DocumentRead.model_validate(doc) for doc in result]

    return documents


@app.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, session: SessionDep, _: APIKeyDep):
    """
    Get a document by ID including its tags
    """
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@app.post("/documents/{document_id}/tags", response_model=DocumentRead)
def add_tags_to_document(
    document_id: int, tags_data: DocumentAddTags, session: SessionDep, _: APIKeyDep
):
    """
    Add tags to an existing document
    """
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify all tags exist
    new_tags = session.exec(select(Tag).where(Tag.id.in_(tags_data.tag_ids))).all()
    if len(new_tags) != len(tags_data.tag_ids):
        raise HTTPException(status_code=400, detail="One or more tag IDs do not exist")

    # Add new tags to existing ones
    existing_tag_ids = {tag.id for tag in document.tags}
    for tag in new_tags:
        if tag.id not in existing_tag_ids:
            document.tags.append(tag)

    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@app.post("/documents/", response_model=DocumentRead, status_code=201)
def create_document(document_data: DocumentCreate, session: SessionDep, _: APIKeyDep):
    """
    Create a new document with optional tags
    """
    # First verify all tags exist

    if document_data.tag_ids:
        tags = session.exec(select(Tag).where(Tag.id.in_(document_data.tag_ids))).all()
        if len(tags) != len(document_data.tag_ids):
            raise HTTPException(
                status_code=400, detail="One or more tag IDs do not exist"
            )
    else:
        tags = []

    # Create the document
    document = Document(
        title=document_data.title,
        description=document_data.description,
        content=document_data.content,
        interestingness=document_data.interestingness,
        tags=tags,
        created_at=document_data.created_at or datetime.utcnow(),
        updated_at=document_data.updated_at or datetime.utcnow(),
    )

    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@app.post("/tags/", response_model=Tag, status_code=201)
def create_tag(tag_data: TagCreate, session: SessionDep, _: APIKeyDep):
    """
    Create a new tag
    """
    tag = Tag(name=tag_data.name, description=tag_data.description)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag
