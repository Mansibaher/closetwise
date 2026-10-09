from app.db import Session, Garment, User
from app.seed import DATA, LEGACY_DATA, PHOTOS, ASSETS
from app.storage import normalize, storage
from sqlalchemy import select

count = 0
with Session() as session:
    for garment in session.scalars(select(Garment).join(User).where(User.demo == True)):
        attrs = garment.attributes.copy()
        if (
            attrs.get("notes")
            != "Original demo illustration; not a clothing photograph."
        ):
            continue
        index = next(
            (i for i, item in enumerate(LEGACY_DATA) if item[0] == attrs.get("name")),
            None,
        )
        if index is None:
            continue
        name, category, slot, color, warmth, formality = DATA[index]
        attrs.update(
            name=name,
            category=category,
            primary_color=color,
            notes=f"Demo photograph: {PHOTOS[index]['source']}. Warmth and formality are manually assigned demo ratings, not inferred from the photo.",
        )
        full, thumb = normalize((ASSETS / PHOTOS[index]["file"]).read_bytes())
        storage().put(garment.image_key, full)
        storage().put(garment.image_key.replace(".webp", "-thumb.webp"), thumb)
        garment.attributes = attrs
        count += 1
    session.commit()
print(f"Updated {count} demo garments; preserved IDs, laundry state and feedback.")
