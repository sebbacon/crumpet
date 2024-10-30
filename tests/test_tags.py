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
    tag1 = Tag(name="python", description="Python programming", documents_count=0)
    tag2 = Tag(name="fastapi", description="FastAPI framework", documents_count=0)
    session.add(tag1)
    session.add(tag2)
    session.commit()

    response = client.get("/tags/", headers={"X-API-Key": "dev_api_key"})
    assert response.status_code == 200
    tags = response.json()
    assert len(tags) == 2
    assert tags[0]["name"] == "python"
    assert tags[1]["name"] == "fastapi"
