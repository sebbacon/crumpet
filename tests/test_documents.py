import tempfile
import os
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
import pytest
from unittest import mock
from app.main import app, get_session, create_db_and_tables
from app.models import Document, Tag
from app.config import Settings


@pytest.fixture(name="settings")
def settings_fixture():
    return Settings(database_url="sqlite:///:memory:", api_key="dev_api_key")


@pytest.fixture(name="engine")
def engine_fixture(settings):
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    create_db_and_tables(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(engine: Session, session: Session, settings: Settings):
    def get_session_override():
        return session

    with (
        mock.patch("app.main.get_settings", return_value=settings),
        mock.patch("app.main.engine", engine),
        mock.patch("app.main.get_session", side_effect=get_session_override),
    ):
        client = TestClient(app)
        yield client


def test_create_document(client: TestClient, session: Session):
    # Create test tags first
    tag1 = Tag(name="python", description="Python programming")
    tag2 = Tag(name="fastapi", description="FastAPI framework")
    session.add_all([tag1, tag2])
    session.commit()

    # Refresh to get the assigned IDs
    session.refresh(tag1)
    session.refresh(tag2)

    # Create a new document with tags
    document_data = {
        "title": "Test Document",
        "description": "This is a test document",
        "content": "Here is the full content of the test document",
        "tag_ids": [tag1.id, tag2.id],
    }

    response = client.post(
        "/documents/", headers={"X-API-Key": "dev_api_key"}, json=document_data
    )

    assert response.status_code == 201
    created_doc = response.json()
    assert created_doc["title"] == document_data["title"]
    assert created_doc["description"] == document_data["description"]
    assert created_doc["content"] == document_data["content"]
    assert len(created_doc["tags"]) == 2


def test_get_document(client: TestClient, session: Session):
    # Create test tags
    tag1 = Tag(name="python", description="Python programming")
    tag2 = Tag(name="fastapi", description="FastAPI framework")
    session.add(tag1)
    session.add(tag2)
    session.commit()
    session.refresh(tag1)
    session.refresh(tag2)

    # Create test document with tags
    document = Document(
        title="Test Document",
        description="This is a test document",
        content="Here is the content",
        tags=[tag1, tag2],
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    # Get the document
    response = client.get(
        f"/documents/{document.id}", headers={"X-API-Key": "dev_api_key"}
    )

    assert response.status_code == 200
    doc_data = response.json()
    assert doc_data["title"] == "Test Document"
    assert doc_data["description"] == "This is a test document"
    assert doc_data["content"] == "Here is the content"
    assert len(doc_data["tags"]) == 2
    assert doc_data["tags"][0]["name"] == "python"
    assert doc_data["tags"][0]["description"] == "Python programming"
    assert doc_data["tags"][1]["name"] == "fastapi"
    assert doc_data["tags"][1]["description"] == "FastAPI framework"


def test_get_document_not_found(client: TestClient):
    response = client.get("/documents/999", headers={"X-API-Key": "dev_api_key"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_create_document_invalid_tags(client: TestClient):
    document_data = {
        "title": "Test Document",
        "description": "This is a test document",
        "content": "Here is the full content of the test document",
        "tag_ids": [999],  # Non-existent tag ID
    }

    response = client.post(
        "/documents/", headers={"X-API-Key": "dev_api_key"}, json=document_data
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "One or more tag IDs do not exist"


def test_add_tags_to_document(client: TestClient, session: Session):
    # Create test tags
    tag1 = Tag(name="python", description="Python programming")
    tag2 = Tag(name="fastapi", description="FastAPI framework")
    tag3 = Tag(name="api", description="API development")
    session.add_all([tag1, tag2, tag3])
    session.commit()

    # Create test document with initial tags
    document = Document(
        title="Test Document",
        description="This is a test document",
        content="Here is the content",
        tags=[tag1],
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    # Add new tags to the document
    response = client.post(
        f"/documents/{document.id}/tags",
        headers={"X-API-Key": "dev_api_key"},
        json={"tag_ids": [tag2.id, tag3.id]},
    )

    assert response.status_code == 200
    doc_data = response.json()
    assert len(doc_data["tags"]) == 3
    tag_names = {tag["name"] for tag in doc_data["tags"]}
    assert tag_names == {"python", "fastapi", "api"}


def test_add_tags_to_nonexistent_document(client: TestClient):
    response = client.post(
        "/documents/999/tags",
        headers={"X-API-Key": "dev_api_key"},
        json={"tag_ids": [1]},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_search_documents(client: TestClient, session: Session):
    # Create test tags
    tag1 = Tag(name="python", description="Python programming")
    tag2 = Tag(name="fastapi", description="FastAPI framework")
    session.add_all([tag1, tag2])
    session.commit()

    # Create test documents with tags
    doc1 = Document(
        title="Python Tutorial",
        description="Learn Python programming",
        content="This is a Python tutorial",
        tags=[tag1],
    )
    doc2 = Document(
        title="FastAPI Guide",
        description="Build APIs with FastAPI",
        content="FastAPI tutorial content",
        tags=[tag2],
    )
    doc3 = Document(
        title="Database Guide",
        description="Working with databases",
        content="Database tutorial content",
        tags=[],
    )
    session.add_all([doc1, doc2, doc3])
    session.commit()

    # Commit and wait a moment for FTS index to update
    session.commit()

    # Search by title
    response = client.get(
        "/documents/search?q=Python", headers={"X-API-Key": "dev_api_key"}
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["title"] == "Python Tutorial"

    # Search by tag
    response = client.get(
        "/documents/search?q=fastapi", headers={"X-API-Key": "dev_api_key"}
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["title"] == "FastAPI Guide"

    # Search by content
    response = client.get(
        "/documents/search?q=database", headers={"X-API-Key": "dev_api_key"}
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["title"] == "Database Guide"


def test_add_nonexistent_tags_to_document(client: TestClient, session: Session):
    # Create test document
    document = Document(
        title="Test Document",
        description="This is a test document",
        content="Here is the content",
    )
    session.add(document)
    session.commit()

    # Try to add non-existent tags
    response = client.post(
        f"/documents/{document.id}/tags",
        headers={"X-API-Key": "dev_api_key"},
        json={"tag_ids": [999]},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "One or more tag IDs do not exist"


def test_settings_mock(client: TestClient):
    """Test that settings have been mocked correctly"""
    response = client.get("/documents/999", headers={"X-API-Key": "dev_api_key"})
    assert response.status_code == 404  # Verifies API key was accepted
