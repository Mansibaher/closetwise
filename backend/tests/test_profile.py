from app.schemas import Context


def test_profile_survives_login_and_is_private(client):
    credentials = {"email": "person@example.com", "password": "strong-password"}
    assert client.post("/auth/register", json=credentials).status_code == 200
    profile = {
        "display_name": "Alex",
        "outfit_style": "men",
        "default_occasion": "weekend",
    }
    assert client.put("/profile", json=profile).json()["profile"] == profile
    client.post("/auth/logout")
    assert client.get("/auth/me").status_code == 401
    assert client.post("/auth/login", json=credentials).json()["profile"] == profile
    assert client.get("/auth/me").json()["profile"] == profile
    assert (
        client.put("/profile", json={**profile, "outfit_style": "invalid"}).status_code
        == 422
    )
    client.post("/auth/logout")
    other = client.post(
        "/auth/register",
        json={"email": "other@example.com", "password": "strong-password"},
    ).json()
    assert other["profile"]["display_name"] == ""
    assert other["profile"]["outfit_style"] == "all"
    assert client.get("/garments").json() == []


def test_style_filters_boards_requirements_and_adjustments(demo):
    original = demo.post("/outfits/generate", json=Context().model_dump()).json()[
        "outfits"
    ]
    for style in ("men", "women"):
        assert (
            demo.put(
                "/profile", json={"display_name": "Alex", "outfit_style": style}
            ).status_code
            == 200
        )
        result = demo.post("/outfits/generate", json=Context().model_dump())
        assert result.status_code == 200, result.text
        assert result.json()["outfits"]
        for outfit in result.json()["outfits"]:
            assert all(g["audience"] in (style, "unisex") for g in outfit["garments"])
            adjustment = demo.post(
                f"/outfits/{outfit['id']}/adjust", json={"direction": "casual"}
            )
            if adjustment.status_code == 200:
                assert all(
                    g["audience"] in (style, "unisex")
                    for g in adjustment.json()["outfit"]["garments"]
                )
        incompatible = next(
            g
            for g in demo.get("/garments").json()
            if g["audience"] not in (style, "unisex") and g["laundry"] == "clean"
        )
        context = Context(required=[incompatible["id"]]).model_dump()
        assert demo.post("/outfits/generate", json=context).status_code == 409
    assert original
