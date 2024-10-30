from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
import pytest
from app.main import app, get_session
from app.models import Tag
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

def test_list_tags_unauthorized(client: TestClient):
    response = client.get("/tags/")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

def test_list_tags_empty(client: TestClient):
    response = client.get("/tags/", headers={"X-API-Key": "dev_api_key"})
    assert response.status_code == 200
    assert response.json() == []

def test_list_tags_with_data(session: Session, client: TestClient):
    # Create test tags
    tag1 = Tag(name="python", description="Python programming")
    
    tag2 = Tag(name="fastapi", description="FastAPI framework")
    session.add(tag1)
    session.add(tag2)
    session.commit()

    response = client.get("/tags/", headers={"X-API-Key": "dev_api_key"})
    assert response.status_code == 200
    tags = response.json()
    assert len(tags) == 2
    assert tags[0]["name"] == "python"
    assert tags[1]["name"] == "fastapi"
    assert tags[0]["documents_count"] == 0
  

def test_create_tag(client: TestClient):
    tag_data = {
        "name": "docker",
        "description": "Docker containers"
    }
    response = client.post(
        "/tags/",
        headers={"X-API-Key": "dev_api_key"},
        json=tag_data
    )
    assert response.status_code == 201
    created_tag = response.json()
    assert created_tag["name"] == tag_data["name"]
    assert created_tag["description"] == tag_data["description"]
    assert "id" in created_tag

def test_update_tag_description(client: TestClient, session: Session):
    # Create test tag
    tag = Tag(name="python", description="Old description")
    session.add(tag)
    session.commit()
    session.refresh(tag)

    # Update the tag
    update_data = {"description": "New description"}
    response = client.patch(
        f"/tags/{tag.id}",
        headers={"X-API-Key": "dev_api_key"},
        json=update_data
    )
    assert response.status_code == 200
    updated_tag = response.json()
    assert updated_tag["description"] == "New description"
    assert updated_tag["name"] == "python"  # Name should remain unchanged

def test_update_tag_not_found(client: TestClient):
    update_data = {"description": "New description"}
    response = client.patch(
        "/tags/999",
        headers={"X-API-Key": "dev_api_key"},
        json=update_data
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Tag not found"

def test_create_tag_unauthorized(client: TestClient):
    tag_data = {
        "name": "docker",
        "description": "Docker containers"
    }
    response = client.post("/tags/", json=tag_data)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"
