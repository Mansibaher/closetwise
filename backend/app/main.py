import os
import logging
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Response, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import select, delete
from sqlalchemy.orm import Session as DBSession
from .db import (
    session,
    User,
    Garment,
    Suggestion,
    Outfit,
    OutfitItem,
    Feedback,
    Preference,
    now,
)
from .schemas import (
    Attributes,
    Context,
    Credentials,
    UserView,
    Profile,
    GarmentView,
    GarmentInput,
    ArchiveInput,
    AnalysisView,
    OutfitView,
    GenerateView,
    AdjustmentView,
    AdjustmentInput,
    FeedbackInput,
    FeedbackView,
    InsightsView,
)
from .auth import current, passwords, set_cookie
from .storage import save_image, storage
from .recognition import provider
from . import engine

app = FastAPI(
    title="ClosetWise",
    version="1.0.0",
    description="Private wardrobe, deterministic constraints, explainable content ranking.",
)


@app.middleware("http")
async def origin_guard(request: Request, call_next):
    origin = request.headers.get("origin")
    allowed = set(
        os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
    )
    if (
        request.method not in ("GET", "HEAD", "OPTIONS")
        and origin
        and origin not in allowed
    ):
        return JSONResponse(
            status_code=403,
            content={
                "detail": {
                    "code": "INVALID_ORIGIN",
                    "message": "Request origin is not permitted.",
                }
            },
        )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "INVALID_GARMENT_ATTRIBUTES"
                if "/garments" in request.url.path
                else "INVALID_REQUEST",
                "message": "; ".join(
                    f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()
                ),
            }
        },
    )


def fail(code, message, status=409):
    raise HTTPException(status, detail={"code": code, "message": message})


def owned(s, cls, id, user):
    obj = s.get(cls, id)
    if not obj or obj.owner_id != user.id:
        fail("NOT_FOUND", "Record not found.", 404)
    return obj


def garment_view(g):
    return {
        **g.attributes,
        "id": g.id,
        "archived": g.archived,
        "image_url": f"/api/images/{g.image_key}" if g.image_key else None,
        "thumbnail_url": f"/api/images/{g.image_key.replace('.webp', '-thumb.webp')}"
        if g.image_key
        else None,
    }


def data(g):
    return {**g.attributes, "id": g.id, "owner_id": g.owner_id, "archived": g.archived}


def wardrobe(s, user):
    style = (user.profile or {}).get("outfit_style", "all")
    return [
        data(g)
        for g in s.scalars(select(Garment).where(Garment.owner_id == user.id))
        if style == "all" or g.attributes.get("audience", "unisex") in (style, "unisex")
    ]


def preference(s, user):
    p = s.get(Preference, user.id)
    if not p:
        p = Preference(owner_id=user.id, vector=[0.0] * 4, count=0)
        s.add(p)
        s.flush()
    return p


def persist(s, user, items, c, scores, parent=None):
    snapshots = [garment_view(s.get(Garment, g["id"])) for g in items]
    o = Outfit(
        owner_id=user.id,
        context=c.model_dump(),
        scores=scores,
        snapshots=snapshots,
        parent_id=parent,
    )
    s.add(o)
    s.flush()
    for g in items:
        s.add(OutfitItem(outfit_id=o.id, garment_id=g["id"], slot=g["slot"]))
    s.commit()
    return o


def outfit_view(o):
    c = Context(**o.context)
    warmth = sum(
        g["warmth"] for g in o.snapshots if g["slot"] not in ("shoes", "accessory")
    )
    lo, hi = engine.weather_bounds(c)
    return {
        "id": o.id,
        "context": o.context,
        "garments": o.snapshots,
        "scores": o.scores,
        "parent_id": o.parent_id,
        "explanations": [
            f"Body warmth {warmth} fits the {lo}–{hi} range at {c.temperature:g}°C and {c.wind:g} km/h wind.",
            f"Every garment meets your formality bounds {c.min_formality}–{c.max_formality} and was clean and owned by you when generated.",
            f"Color harmony {o.scores['color']:.2f}; formality coherence {o.scores['coherence']:.2f}. Occasion is a label; your editable bounds are authoritative.",
        ],
    }


@app.get("/health")
def health(s: DBSession = Depends(session)):
    s.execute(select(1))
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserView)
def register(body: Credentials, response: Response, s: DBSession = Depends(session)):
    email = body.email.lower()
    if s.scalar(select(User).where(User.email == email)):
        fail("EMAIL_EXISTS", "That email is already registered.")
    user = User(email=email, password_hash=passwords.hash(body.password))
    s.add(user)
    s.commit()
    set_cookie(response, user)
    return user


@app.post("/auth/login", response_model=UserView)
def login(body: Credentials, response: Response, s: DBSession = Depends(session)):
    user = s.scalar(select(User).where(User.email == body.email.lower()))
    # Always verify a hash to reduce account-enumeration timing differences.
    if not passwords.verify(body.password, user.password_hash if user else DUMMY_HASH):
        fail("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)
    if not user:
        fail("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)
    set_cookie(response, user)
    return user


DUMMY_HASH = passwords.hash("not-a-real-account-password")


@app.post("/auth/demo", response_model=UserView)
def demo(response: Response, s: DBSession = Depends(session)):
    if os.getenv("DEMO_ENABLED", "true") != "true":
        fail("DEMO_DISABLED", "Demo access is disabled.", 403)
    from .seed import seed

    # Each demo visitor receives an isolated wardrobe and reset scope.
    from uuid import uuid4

    user = User(
        email=f"demo-{uuid4()}@closetwise.local", password_hash=DUMMY_HASH, demo=True
    )
    s.add(user)
    s.commit()
    seed(s, user)
    set_cookie(response, user)
    return user


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("closetwise_session", path="/")
    return {"ok": True}


@app.get("/auth/me", response_model=UserView)
def me(user: User = Depends(current)):
    return user


@app.put("/profile", response_model=UserView)
def save_profile(
    body: Profile, user: User = Depends(current), s: DBSession = Depends(session)
):
    account = s.get(User, user.id)
    account.profile = body.model_dump()
    s.commit()
    return account


@app.post("/demo/reset")
def reset_demo(user: User = Depends(current), s: DBSession = Depends(session)):
    if not user.demo:
        fail("DEMO_ONLY", "Only demo accounts can reset demo data.", 403)
    from .seed import reset

    reset(s, user)
    return {"ok": True}


@app.get("/garments", response_model=list[GarmentView])
def list_garments(
    category: str | None = None,
    color: str | None = None,
    warmth: int | None = None,
    formality: int | None = None,
    laundry: str | None = None,
    archived: bool = False,
    user: User = Depends(current),
    s: DBSession = Depends(session),
):
    records = s.scalars(
        select(Garment)
        .where(Garment.owner_id == user.id, Garment.archived == archived)
        .order_by(Garment.created_at)
    )
    return [
        garment_view(g)
        for g in records
        if all(
            v is None or g.attributes[k] == v
            for k, v in [
                ("category", category),
                ("primary_color", color),
                ("warmth", warmth),
                ("formality", formality),
                ("laundry", laundry),
            ]
        )
    ]


@app.post("/garments", response_model=GarmentView)
def create_garment(
    body: GarmentInput, user: User = Depends(current), s: DBSession = Depends(session)
):
    suggestion = (
        owned(s, Suggestion, body.suggestion_id, user) if body.suggestion_id else None
    )
    if suggestion and suggestion.garment_id:
        fail("SUGGESTION_USED", "This upload was already saved.")
    attrs = body.model_dump(exclude={"suggestion_id"})
    g = Garment(
        owner_id=user.id,
        attributes=attrs,
        slot=body.slot,
        laundry=body.laundry,
        image_key=suggestion.image_key if suggestion else None,
    )
    s.add(g)
    s.flush()
    if suggestion:
        suggestion.garment_id = g.id
        suggestion.confirmed = attrs
    s.commit()
    return garment_view(g)


@app.put("/garments/{id}", response_model=GarmentView)
def edit_garment(
    id: str,
    body: Attributes,
    user: User = Depends(current),
    s: DBSession = Depends(session),
):
    g = owned(s, Garment, id, user)
    g.attributes = body.model_dump()
    g.slot = body.slot
    g.laundry = body.laundry
    s.commit()
    return garment_view(g)


@app.patch("/garments/{id}/archive", response_model=GarmentView)
def archive(
    id: str,
    body: ArchiveInput,
    user: User = Depends(current),
    s: DBSession = Depends(session),
):
    g = owned(s, Garment, id, user)
    g.archived = body.archived
    s.commit()
    return garment_view(g)


@app.delete("/garments/{id}")
def remove(id: str, user: User = Depends(current), s: DBSession = Depends(session)):
    g = owned(s, Garment, id, user)
    key = g.image_key
    s.execute(delete(Suggestion).where(Suggestion.garment_id == id))
    s.delete(g)
    s.commit()
    if key:
        storage().delete(key)
        storage().delete(key.replace(".webp", "-thumb.webp"))
    return {"ok": True}


@app.post("/uploads", response_model=AnalysisView)
def upload(
    file: UploadFile = File(...),
    user: User = Depends(current),
    s: DBSession = Depends(session),
):
    raw = file.file.read(8 * 1024 * 1024 + 1)
    try:
        key = save_image(raw)
    except ValueError as e:
        logging.getLogger("uvicorn.error").warning("Upload rejected: %s; bytes=%s; type=%s", str(e), len(raw), file.content_type)
        fail("INVALID_IMAGE", str(e), 422)
    p = provider()
    warning = None
    try:
        proposed, uncertainty = p.analyze(storage().get(key))
        proposed = Attributes.model_validate(proposed)
    except Exception:
        proposed = Attributes(
            name="New garment",
            category="shirt",
            slot="top",
            primary_color="white",
            warmth=1,
            formality=2,
        )
        uncertainty = None
        warning = "RECOGNITION_UNAVAILABLE: analysis failed; enter attributes manually."
    suggestion = Suggestion(
        owner_id=user.id, image_key=key, provider=p.name, proposed=proposed.model_dump()
    )
    s.add(suggestion)
    s.commit()
    return {
        "id": suggestion.id,
        "provider": p.name,
        "proposed": proposed,
        "uncertainty": uncertainty,
        "warning": warning,
        "image_url": f"/api/images/{key}",
    }


@app.get("/images/{key}")
def image(key: str, user: User = Depends(current), s: DBSession = Depends(session)):
    original = key.replace("-thumb.webp", ".webp")
    if not (
        s.scalar(
            select(Garment.id).where(
                Garment.owner_id == user.id, Garment.image_key == original
            )
        )
        or s.scalar(
            select(Suggestion.id).where(
                Suggestion.owner_id == user.id, Suggestion.image_key == original
            )
        )
    ):
        fail("NOT_FOUND", "Image not found.", 404)
    try:
        raw = storage().get(key)
    except (FileNotFoundError, ValueError):
        fail("NOT_FOUND", "Image not found.", 404)
    return Response(
        raw, media_type="image/webp", headers={"Cache-Control": "private, no-store"}
    )


@app.post("/outfits/generate", response_model=GenerateView)
def generate(
    body: Context, user: User = Depends(current), s: DBSession = Depends(session)
):
    p = preference(s, user)
    recent = {}
    history = []
    for o in s.scalars(
        select(Outfit)
        .where(Outfit.owner_id == user.id)
        .order_by(Outfit.created_at.desc())
        .limit(100)
    ):
        history.append(frozenset(g["id"] for g in o.snapshots))
    for f in s.scalars(
        select(Feedback).where(
            Feedback.owner_id == user.id,
            Feedback.event == "wore",
            Feedback.created_at >= now() - timedelta(days=7),
        )
    ):
        for g in s.get(Outfit, f.outfit_id).snapshots:
            recent[g["id"]] = 1
    ranked, error = engine.candidates(
        wardrobe(s, user), body, user.id, p.vector, recent, history
    )
    if error:
        fail(*error)
    outfits = [
        outfit_view(persist(s, user, items, body, scores))
        for items, scores in engine.diverse(ranked)
    ]
    return {"outfits": outfits, "candidate_count": len(ranked), "approximate": True}


@app.get("/outfits/{id}", response_model=OutfitView)
def get_outfit(id: str, user: User = Depends(current), s: DBSession = Depends(session)):
    return outfit_view(owned(s, Outfit, id, user))


@app.post("/outfits/{id}/adjust", response_model=AdjustmentView)
def adjustment(
    id: str,
    body: AdjustmentInput,
    user: User = Depends(current),
    s: DBSession = Depends(session),
):
    o = owned(s, Outfit, id, user)
    c = Context(**o.context)
    items = []
    for snapshot in o.snapshots:
        g = s.get(Garment, snapshot["id"])
        if not g or g.owner_id != user.id:
            fail(
                "NO_VALID_SINGLE_ITEM_ADJUSTMENT",
                "A garment was deleted. Regenerate the outfit; original board retained.",
            )
        style = (user.profile or {}).get("outfit_style", "all")
        if style != "all" and g.attributes.get("audience", "unisex") not in (
            style,
            "unisex",
        ):
            fail(
                "PROFILE_CHANGED",
                "Your clothing style changed. Generate fresh outfits using your saved profile.",
            )
        items.append(data(g))
    result = engine.adjust(
        items, wardrobe(s, user), c, user.id, body.direction, preference(s, user).vector
    )
    if not result:
        fail(
            "NO_VALID_SINGLE_ITEM_ADJUSTMENT",
            "No same-slot replacement improves this direction while respecting current constraints and fixed items. Original board retained.",
        )
    updated, old, new, explanation = result
    fresh = persist(
        s, user, updated, c, engine.score(updated, c, preference(s, user).vector), o.id
    )
    return {
        "outfit": outfit_view(fresh),
        "original_id": old["id"],
        "replacement_id": new["id"],
        "direction": body.direction,
        "explanation": explanation,
    }


@app.post("/outfits/{id}/feedback", response_model=FeedbackView)
def feedback(
    id: str,
    body: FeedbackInput,
    user: User = Depends(current),
    s: DBSession = Depends(session),
):
    o = owned(s, Outfit, id, user)
    p = preference(s, user)
    p.vector, p.count = engine.update_preferences(
        p.vector, p.count, o.snapshots, body.event, body.reason
    )
    f = Feedback(
        owner_id=user.id,
        outfit_id=id,
        event=body.event,
        reason=body.reason,
        features=engine.features(o.snapshots).tolist(),
    )
    s.add(f)
    s.commit()
    return feedback_view(f)


def feedback_view(f):
    return {
        "id": f.id,
        "outfit_id": f.outfit_id,
        "event": f.event,
        "reason": f.reason,
        "created_at": f.created_at.isoformat(),
    }


@app.get("/feedback", response_model=list[FeedbackView])
def history(user: User = Depends(current), s: DBSession = Depends(session)):
    return [
        feedback_view(f)
        for f in s.scalars(
            select(Feedback)
            .where(Feedback.owner_id == user.id)
            .order_by(Feedback.created_at.desc())
            .limit(200)
        )
    ]


@app.get("/preferences", response_model=InsightsView)
def insights(user: User = Depends(current), s: DBSession = Depends(session)):
    p = preference(s, user)
    s.commit()
    return {
        "vector": p.vector,
        "count": p.count,
        "feature_names": engine.FEATURE_NAMES,
        "explanation": "Signed content evidence shrinks toward a five-event zero prior. Skips do not update preferences. Hard constraints never change.",
    }
