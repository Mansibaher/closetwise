"""Run against a migrated disposable PostgreSQL database, never a production DB."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.db import engine
from app.main import app
from app.schemas import Context

assert engine.dialect.name == "postgresql", (
    "This smoke command requires DATABASE_URL for PostgreSQL"
)
with TestClient(app) as client:
    assert client.post("/auth/demo").status_code == 200
    response = client.post("/outfits/generate", json=Context().model_dump())
    assert response.status_code == 200, response.text
    outfit = response.json()["outfits"][0]
    response = client.post(
        f"/outfits/{outfit['id']}/adjust", json={"direction": "casual"}
    )
    assert response.status_code == 200, response.text
    assert (
        client.post(
            f"/outfits/{outfit['id']}/feedback", json={"event": "liked"}
        ).status_code
        == 200
    )
    assert client.get("/preferences").json()["count"] == 1
    assert client.post("/demo/reset").status_code == 200
print("PostgreSQL migrations, generation, adjustment, feedback and reset passed")
