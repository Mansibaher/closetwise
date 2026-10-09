from pathlib import Path
import pytest

pytest.importorskip("onnxruntime")
pytest.importorskip("tokenizers")
ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    not (ROOT / "models/clip/model.onnx").exists(),
    reason="Optional local model not downloaded",
)


def test_local_model_reads_different_clothing_pixels():
    from app.local_vision import LocalProvider

    model = LocalProvider()
    shirt, note = model.analyze((ROOT / "assets/photos/00.jpg").read_bytes())
    sneakers, _ = model.analyze((ROOT / "assets/photos/17.jpg").read_bytes())
    jeans, _ = model.analyze((ROOT / "assets/photos/11.jpg").read_bytes())
    assert (shirt.category, shirt.primary_color) == ("shirt", "white")
    assert (sneakers.category, sneakers.slot) == ("sneakers", "shoes")
    assert (jeans.category, jeans.primary_color) == ("jeans", "black")
    assert "category defaults" in note
    assert shirt.audience == "unisex"


def test_authenticated_upload_uses_local_model(client, monkeypatch):
    monkeypatch.setenv("RECOGNITION_PROVIDER", "local")
    assert (
        client.post(
            "/auth/register",
            json={"email": "photo@example.com", "password": "test-password"},
        ).status_code
        == 200
    )
    result = client.post(
        "/uploads",
        files={
            "file": (
                "shirt.jpg",
                (ROOT / "assets/photos/00.jpg").read_bytes(),
                "image/jpeg",
            )
        },
    )
    assert result.status_code == 200, result.text
    result = result.json()
    assert result["provider"] == "local" and result["warning"] is None
    assert result["proposed"]["category"] == "shirt"
    saved = client.post(
        "/garments", json={**result["proposed"], "suggestion_id": result["id"]}
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["image_url"] == result["image_url"]
