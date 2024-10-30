from typing import Annotated, List
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlmodel import Session, SQLModel, create_engine, select
from .models import Tag, Document
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
