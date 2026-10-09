from sqlalchemy import select
from app.db import Session, Garment, User
from app.seed import DATA

count = 0
with Session() as s:
    for g in s.scalars(select(Garment).join(User).where(User.demo == True)):
        a = g.attributes.copy()
        if "Demo photograph:" not in a.get("notes", "") or "audience" in a:
            continue
        i = next((i for i, d in enumerate(DATA) if d[0] == a.get("name")), None)
        if i is None:
            continue
        a["audience"] = (
            "women"
            if i in (3, 4, 7, 13, 24, 25, 26, 27)
            else "men"
            if i in (2, 19, 20, 31)
            else "unisex"
        )
        g.attributes = a
        count += 1
    s.commit()
print(f"Labeled {count} demo garments")

