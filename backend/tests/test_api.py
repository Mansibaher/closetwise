import io
from PIL import Image
from app.schemas import Context


def body():
    return Context().model_dump()


def photo():
    im = Image.new("RGB", (200, 250), "blue")
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def test_standout_flow(demo):
    ws = demo.get("/garments").json()
    assert len(ws) == 32
    result = demo.post("/outfits/generate", json=body())
    assert result.status_code == 200, result.text
    outfits = result.json()["outfits"]
    assert len(outfits) == 3
    original = outfits[0]
    result = demo.post(
        f"/outfits/{original['id']}/adjust", json={"direction": "casual"}
    )
    assert result.status_code == 200, result.text
    adjusted = result.json()["outfit"]
    assert (
        len(
            {g["id"] for g in original["garments"]}
            ^ {g["id"] for g in adjusted["garments"]}
        )
        == 2
    )
    feedback = demo.post(f"/outfits/{adjusted['id']}/feedback", json={"event": "liked"})
    assert feedback.status_code == 200
    assert demo.get("/preferences").json()["count"] == 1
    assert demo.get("/feedback").json()[0]["outfit_id"] == adjusted["id"]
    assert demo.post("/demo/reset").status_code == 200
    assert demo.get("/feedback").json() == []


def test_isolation_on_every_resource(demo):
    gs = demo.get("/garments").json()
    g = gs[0]
    o = demo.post("/outfits/generate", json=body()).json()["outfits"][0]
    assert (
        demo.post(
            "/auth/register",
            json={"email": "other@example.com", "password": "correct-password"},
        ).status_code
        == 200
    )
    assert demo.get("/garments").json() == []
    attributes = {
        k: v
        for k, v in g.items()
        if k not in ("id", "archived", "image_url", "thumbnail_url")
    }
    checks = [
        demo.get("/images/" + g["image_url"].split("/")[-1]),
        demo.put("/garments/" + g["id"], json=attributes),
        demo.patch("/garments/" + g["id"] + "/archive", json={"archived": True}),
        demo.delete("/garments/" + g["id"]),
        demo.get("/outfits/" + o["id"]),
        demo.post("/outfits/" + o["id"] + "/adjust", json={"direction": "casual"}),
        demo.post("/outfits/" + o["id"] + "/feedback", json={"event": "liked"}),
    ]
    assert all(r.status_code == 404 for r in checks)
    assert demo.get("/feedback").json() == []


def test_upload_review_provenance_and_private_suggestion(demo):
    result = demo.post("/uploads", files={"file": ("piece.png", photo(), "image/png")})
    assert result.status_code == 200
    suggestion = result.json()
    assert suggestion["provider"] == "mock"
    attrs = {
        **suggestion["proposed"],
        "name": "My confirmed shirt",
        "suggestion_id": suggestion["id"],
    }
    result = demo.post("/garments", json=attrs)
    assert result.status_code == 200
    assert result.json()["name"] == "My confirmed shirt"
    image = demo.get(suggestion["image_url"].replace("/api", ""))
    assert image.status_code == 200
    im = Image.open(io.BytesIO(image.content))
    assert im.format == "WEBP" and not im.getexif()
    assert demo.post("/garments", json=attrs).status_code == 409
    demo.post("/auth/demo")
    assert demo.post("/garments", json=attrs).status_code == 404


def test_invalid_images_attributes_and_manual_fallback(demo, monkeypatch):
    assert (
        demo.post(
            "/uploads", files={"file": ("bad.png", b"not an image", "image/png")}
        ).status_code
        == 422
    )
    from app import main

    class Broken:
        name = "vision"

        def analyze(self, _):
            return {"invalid": "schema"}, None

    monkeypatch.setattr(main, "provider", lambda: Broken())
    r = demo.post("/uploads", files={"file": ("piece.png", photo(), "image/png")})
    assert r.status_code == 200
    assert "RECOGNITION_UNAVAILABLE" in r.json()["warning"]
    a = r.json()["proposed"]
    a["name"] = "Manual piece"
    assert demo.post("/garments", json=a).status_code == 200
    a["slot"] = "shoes"
    assert (
        demo.post("/garments", json=a).json()["detail"]["code"]
        == "INVALID_GARMENT_ATTRIBUTES"
    )


def test_impossible_adjustment_retains_persisted_board(demo):
    result = demo.post("/outfits/generate", json=body()).json()["outfits"][0]
    c = result["context"]
    c["required"] = [g["id"] for g in result["garments"]]
    fixed = demo.post("/outfits/generate", json=c).json()["outfits"][0]
    r = demo.post("/outfits/" + fixed["id"] + "/adjust", json={"direction": "warmer"})
    assert (
        r.status_code == 409
        and r.json()["detail"]["code"] == "NO_VALID_SINGLE_ITEM_ADJUSTMENT"
    )
    assert demo.get("/outfits/" + fixed["id"]).json()["garments"] == fixed["garments"]


def test_dirty_required_archive_delete_and_csrf(demo):
    ws = demo.get("/garments").json()
    dirty = next(g for g in ws if g["laundry"] == "dirty")
    r = demo.post("/outfits/generate", json={**body(), "required": [dirty["id"]]})
    assert r.json()["detail"]["code"] == "REQUIRED_ITEM_UNAVAILABLE"
    g = ws[0]
    assert (
        demo.patch(
            "/garments/" + g["id"] + "/archive", json={"archived": True}
        ).status_code
        == 200
    )
    assert len(demo.get("/garments", params={"archived": True}).json()) == 1
    assert demo.delete("/garments/" + g["id"]).status_code == 200
    assert demo.get(g["image_url"].replace("/api", "")).status_code == 404
    assert (
        demo.post(
            "/auth/demo", headers={"Origin": "https://attacker.example"}
        ).status_code
        == 403
    )


def test_logout_and_authentication(client):
    assert client.get("/garments").status_code == 401
    credentials = {"email": "owner@example.com", "password": "safe-password-123"}
    assert client.post("/auth/register", json=credentials).status_code == 200
    assert client.post("/auth/logout").status_code == 200
    assert client.get("/garments").status_code == 401
    assert (
        client.post(
            "/auth/login", json={**credentials, "password": "bad-password"}
        ).status_code
        == 401
    )
    assert client.post("/auth/login", json=credentials).status_code == 200
