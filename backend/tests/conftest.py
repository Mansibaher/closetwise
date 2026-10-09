import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["STORAGE_PATH"] = "./.test-images"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.db import Base, session
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "images"))
    e = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(e, "connect")
    def fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(e)
    Factory = sessionmaker(e, expire_on_commit=False)

    def override():
        with Factory() as s:
            yield s

    app.dependency_overrides[session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    e.dispose()


@pytest.fixture
def demo(client):
    assert client.post("/auth/demo").status_code == 200
    return client
