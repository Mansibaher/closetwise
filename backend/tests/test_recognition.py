import pytest
import httpx
from pydantic import ValidationError
from app.recognition import MockProvider, VisionProvider
from app.schemas import Attributes


def test_mock_is_deterministic_and_not_pixel_recognition():
    p = MockProvider()
    a, u = p.analyze(b"one")
    b, v = p.analyze(b"two")
    assert a == b and "not inferred" in u and u == v


def test_real_provider_schema_and_server_key(monkeypatch):
    monkeypatch.setenv("VISION_API_KEY", "test-key-never-used-on-network")
    attributes = Attributes(
        name="Reviewed blouse",
        category="shirt",
        slot="top",
        primary_color="white",
        warmth=1,
        formality=3,
    ).model_dump()

    def post(url, headers, json: dict, timeout):
        assert headers["Authorization"] == "Bearer test-key-never-used-on-network"
        assert json["messages"][1]["content"][0]["image_url"]["url"].startswith(
            "data:image/webp;base64,"
        )
        assert timeout == 25 and json["response_format"]["type"] == "json_schema"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": __import__("json").dumps(attributes)}}
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", post)
    result, uncertainty = VisionProvider().analyze(b"image")
    assert result.name == "Reviewed blouse" and uncertainty is None
    attributes["confidence"] = 0.99
    with pytest.raises(ValidationError):
        VisionProvider().analyze(b"image")
