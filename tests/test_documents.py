from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
import pytest
from app.main import app, get_session
from app.models import Document, Tag
from app.config import get_settings, Settings

def get_test_settings():
    return Settings(database_url="sqlite://")

app.dependency_overrides[get_settings] = get_test_settings

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_create_document(client: TestClient, session: Session):
    # Create test tags first
    tag1 = Tag(name="python", description="Python programming")
    tag2 = Tag(name="fastapi", description="FastAPI framework")
    session.add(tag1)
    session.add(tag2)
    session.commit()
    session.refresh(tag1)
    session.refresh(tag2)

    # Create a new document with tags
    document_data = {
        "title": "Test Document",
        "description": "This is a test document",
        "content": "Here is the full content of the test document",
        "tag_ids": [tag1.id, tag2.id]
    }
    
    response = client.post(
        "/documents/",
        headers={"X-API-Key": "dev_api_key"},
        json=document_data
    )
    
    assert response.status_code == 201
    created_doc = response.json()
    assert created_doc["title"] == document_data["title"]
    assert created_doc["description"] == document_data["description"]
    assert created_doc["content"] == document_data["content"]
    assert len(created_doc["tags"]) == 2
    
    # Verify tags were updated
    for tag_id in document_data["tag_ids"]:
        tag = session.get(Tag, tag_id)
        assert tag.documents_count == 1

def test_create_document_invalid_tags(client: TestClient):
    document_data = {
        "title": "Test Document",
        "description": "This is a test document",
        "content": "Here is the full content of the test document",
        "tag_ids": [999]  # Non-existent tag ID
    }
    
    response = client.post(
        "/documents/",
        headers={"X-API-Key": "dev_api_key"},
        json=document_data
    )
    
    assert response.status_code == 400
    assert response.json()["detail"] == "One or more tag IDs do not exist"
