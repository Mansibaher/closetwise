"""Locally bundled demo photographs; legacy CC0 illustration generator."""

from pathlib import Path
import json

from PIL import Image, ImageDraw
import io
from sqlalchemy import select, delete
from .db import (
    User,
    Garment,
    Suggestion,
    Outfit,
    Feedback,
    Preference,
    OutfitItem,
    Session,
)
from .auth import passwords
from .storage import storage
from uuid import uuid4
from .schemas import Attributes

COLORS = {
    "navy": "#263650",
    "white": "#eee9e0",
    "black": "#303034",
    "gray": "#93999c",
    "beige": "#cdbb9e",
    "brown": "#855e46",
    "blue": "#7698b5",
    "green": "#738773",
    "red": "#b66c65",
    "pink": "#d4a3ae",
    "purple": "#9381a4",
    "yellow": "#d4b872",
}
LEGACY_DATA = [
    ("Oxford shirt", "shirt", "top", "white", 1, 4),
    ("Blue button-down", "shirt", "top", "blue", 1, 3),
    ("Fine knit polo", "knit", "top", "navy", 2, 2),
    ("Merino crewneck", "knit", "top", "gray", 3, 3),
    ("Cream cardigan", "knit", "top", "beige", 4, 3),
    ("Sage tee", "shirt", "top", "green", 0, 0),
    ("Striped tee", "shirt", "top", "blue", 1, 1),
    ("Rose blouse", "shirt", "top", "pink", 1, 3),
    ("Charcoal trousers", "trousers", "bottom", "gray", 2, 4),
    ("Navy chinos", "trousers", "bottom", "navy", 2, 3),
    ("Sand chinos", "trousers", "bottom", "beige", 2, 2),
    ("Dark denim", "jeans", "bottom", "blue", 2, 1),
    ("Black wool trousers", "trousers", "bottom", "black", 3, 4),
    ("Midi skirt", "skirt", "bottom", "brown", 1, 3),
    ("Leather loafers", "loafers", "shoes", "brown", 1, 4),
    ("Black derby loafers", "loafers", "shoes", "black", 1, 3),
    ("Smart suede shoes", "loafers", "shoes", "navy", 1, 2),
    ("White sneakers", "sneakers", "shoes", "white", 1, 1),
    ("Weather boots", "boots", "shoes", "black", 3, 3),
    ("Navy blazer", "jacket", "outerwear", "navy", 2, 4),
    ("Soft gray blazer", "jacket", "outerwear", "gray", 2, 3),
    ("Chore jacket", "jacket", "outerwear", "beige", 2, 2),
    ("Camel wool coat", "coat", "outerwear", "brown", 4, 4),
    ("Rain trench", "coat", "outerwear", "beige", 3, 3),
    ("Navy wrap dress", "dress", "onepiece", "navy", 3, 3),
    ("Black knit dress", "dress", "onepiece", "black", 4, 4),
    ("Linen jumpsuit", "jumpsuit", "onepiece", "green", 1, 2),
    ("Floral summer dress", "dress", "onepiece", "pink", 0, 1),
    ("Wool scarf", "scarf", "accessory", "gray", 3, 3),
    ("Leather tote", "bag", "accessory", "brown", 0, 3),
    ("Laundry Oxford", "shirt", "top", "white", 1, 4),
    ("Unavailable blazer", "jacket", "outerwear", "black", 3, 4),
]
DATA = [
    ("Oxford shirt", "shirt", "top", "white", 1, 4),
    ("Blue button-down", "shirt", "top", "blue", 1, 3),
    ("Navy short-sleeve shirt", "shirt", "top", "navy", 2, 2),
    ("Cream tie-neck cardigan", "knit", "top", "beige", 3, 3),
    ("Cream cardigan", "knit", "top", "beige", 4, 3),
    ("Sage tee", "shirt", "top", "green", 0, 0),
    ("Red striped shirt", "shirt", "top", "red", 1, 1),
    ("Rose blouse", "shirt", "top", "pink", 1, 3),
    ("Charcoal trousers", "trousers", "bottom", "gray", 2, 4),
    ("Navy tailored trousers", "trousers", "bottom", "navy", 2, 3),
    ("Sand trousers", "trousers", "bottom", "beige", 2, 2),
    ("Dark denim", "jeans", "bottom", "black", 2, 1),
    ("Black tailored trousers", "trousers", "bottom", "black", 3, 4),
    ("Brown skirt", "skirt", "bottom", "brown", 1, 3),
    ("Brown dress shoes", "dress_shoes", "shoes", "brown", 1, 4),
    ("Black dress shoes", "dress_shoes", "shoes", "black", 1, 3),
    ("Brown derby shoes", "dress_shoes", "shoes", "brown", 1, 2),
    ("White sneakers", "sneakers", "shoes", "white", 1, 1),
    ("Weather boots", "boots", "shoes", "white", 3, 3),
    ("Navy blazer", "jacket", "outerwear", "navy", 2, 4),
    ("Soft gray blazer", "jacket", "outerwear", "gray", 2, 3),
    ("Beige relaxed blazer", "jacket", "outerwear", "beige", 2, 2),
    ("Warm beige coat", "coat", "outerwear", "beige", 4, 4),
    ("Rain trench", "coat", "outerwear", "beige", 3, 3),
    ("Blue tie-front dress", "dress", "onepiece", "blue", 3, 3),
    ("Black belted dress", "dress", "onepiece", "black", 4, 4),
    ("Green jumpsuit", "jumpsuit", "onepiece", "green", 1, 2),
    ("Floral summer dress", "dress", "onepiece", "beige", 0, 1),
    ("Cozy knit scarf", "scarf", "accessory", "gray", 3, 3),
    ("Brown shoulder bag", "bag", "accessory", "brown", 0, 3),
    ("Laundry Oxford", "shirt", "top", "white", 1, 4),
    ("Unavailable blazer", "jacket", "outerwear", "blue", 3, 4),
]
ASSETS = Path(__file__).resolve().parent.parent / "assets"
PHOTOS = json.loads((ASSETS / "photo-manifest.json").read_text())


def illustration(slot, color, pattern="solid"):
    im = Image.new("RGB", (480, 560), "#f2f0eb")
    d = ImageDraw.Draw(im)
    fill = COLORS[color]
    outline = "#45484a"
    d.ellipse((90, 480, 390, 515), fill="#e2e0da")
    if slot in ("top", "outerwear"):
        d.polygon(
            [
                (160, 110),
                (205, 88),
                (240, 115),
                (275, 88),
                (320, 110),
                (405, 220),
                (348, 254),
                (315, 196),
                (315, 425),
                (165, 425),
                (165, 196),
                (132, 254),
                (75, 220),
            ],
            fill=fill,
            outline=outline,
            width=3,
        )
        d.line(
            [(205, 88), (218, 130), (240, 115), (262, 130), (275, 88)],
            fill=outline,
            width=3,
        )
        if slot == "outerwear":
            d.line((240, 118, 240, 425), fill=outline, width=3)
            for y in range(180, 400, 55):
                d.ellipse((248, y, 254, y + 6), fill=outline)
    elif slot == "bottom":
        d.polygon(
            [
                (155, 105),
                (325, 105),
                (340, 445),
                (260, 445),
                (240, 260),
                (220, 445),
                (140, 445),
            ],
            fill=fill,
            outline=outline,
            width=3,
        )
        d.line((155, 140, 325, 140), fill=outline, width=3)
    elif slot == "onepiece":
        d.polygon(
            [
                (175, 100),
                (210, 88),
                (240, 116),
                (270, 88),
                (305, 100),
                (325, 210),
                (283, 227),
                (310, 450),
                (170, 450),
                (197, 227),
                (155, 210),
            ],
            fill=fill,
            outline=outline,
            width=3,
        )
        d.line((195, 225, 285, 225), fill=outline, width=3)
    elif slot == "shoes":
        for x, y in [(90, 230), (245, 280)]:
            d.rounded_rectangle(
                (x, y, x + 130, y + 100), radius=30, fill=fill, outline=outline, width=3
            )
            d.line((x + 8, y + 83, x + 122, y + 83), fill="#faf9f5", width=9)
            for offset in (30, 43, 56):
                d.line((x + 45, y + offset, x + 90, y + offset), fill=outline, width=3)
    else:
        d.arc((155, 110, 325, 300), 180, 360, fill=outline, width=12)
        d.rounded_rectangle(
            (125, 220, 355, 420), radius=15, fill=fill, outline=outline, width=3
        )
    if pattern == "striped":
        for y in range(200, 400, 30):
            d.line((173, y, 305, y), fill="#dadbd8", width=8)
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def seed(s, user):
    for i, (name, category, slot, color, warmth, formality) in enumerate(DATA):
        pattern = (
            "striped"
            if "striped" in name.lower()
            else "floral"
            if "Floral" in name
            else "solid"
        )
        a = Attributes(
            name=name,
            audience="women"
            if i in (3, 4, 7, 13, 24, 25, 26, 27)
            else "men"
            if i in (2, 19, 20, 31)
            else "unisex",
            category=category,
            slot=slot,
            primary_color=color,
            warmth=warmth,
            formality=formality,
            pattern=pattern,
            weather=["dry", "rain", "wind"]
            if name in ("Weather boots", "Rain trench")
            else ["dry", "wind"],
            seasons=["spring", "autumn", "winter"]
            if warmth >= 2
            else ["spring", "summer"],
            laundry="dirty" if i == 30 else "unavailable" if i == 31 else "clean",
            notes=f"Demo photograph: {PHOTOS[i]['source']}. Warmth and formality are manually assigned demo ratings, not inferred from the photo.",
        )
        photo = ASSETS / PHOTOS[i]["file"]
        image_key = f"{uuid4()}.webp"
        storage().put(image_key, photo.with_suffix(".webp").read_bytes())
        storage().put(
            image_key.replace(".webp", "-thumb.webp"),
            photo.with_name(photo.stem + "-thumb.webp").read_bytes(),
        )
        s.add(
            Garment(
                owner_id=user.id,
                attributes=a.model_dump(),
                slot=slot,
                laundry=a.laundry,
                image_key=image_key,
            )
        )
    s.add(Preference(owner_id=user.id, vector=[0.0] * 4, count=0))
    s.commit()


def reset(s, user):
    keys = [
        g.image_key
        for g in s.scalars(select(Garment).where(Garment.owner_id == user.id))
        if g.image_key
    ]
    keys.extend(
        s.scalars(select(Suggestion.image_key).where(Suggestion.owner_id == user.id))
    )
    s.execute(delete(Feedback).where(Feedback.owner_id == user.id))
    ids = list(s.scalars(select(Outfit.id).where(Outfit.owner_id == user.id)))
    if ids:
        s.execute(delete(OutfitItem).where(OutfitItem.outfit_id.in_(ids)))
    s.execute(delete(Outfit).where(Outfit.owner_id == user.id))
    s.execute(delete(Suggestion).where(Suggestion.owner_id == user.id))
    s.execute(delete(Garment).where(Garment.owner_id == user.id))
    s.execute(delete(Preference).where(Preference.owner_id == user.id))
    s.commit()
    for key in set(keys):
        storage().delete(key)
        storage().delete(key.replace(".webp", "-thumb.webp"))
    seed(s, user)


if __name__ == "__main__":
    import sys

    with Session() as s:
        user = s.scalar(select(User).where(User.email == "demo@closetwise.local"))
        if not user:
            user = User(
                email="demo@closetwise.local",
                password_hash=passwords.hash("closetwise-demo"),
                demo=True,
            )
            s.add(user)
            s.commit()
            seed(s, user)
        elif "--reset" in sys.argv:
            reset(s, user)
    print("Demo ready: demo@closetwise.local / closetwise-demo")

