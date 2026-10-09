import os
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    create_engine,
    event,
    ForeignKey,
    String,
    JSON,
    DateTime,
    Boolean,
    Integer,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Timestamp:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class User(Base, Timestamp):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    demo: Mapped[bool] = mapped_column(Boolean, default=False)
    profile: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")


class Garment(Base, Timestamp):
    __tablename__ = "garments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    attributes: Mapped[dict] = mapped_column(JSON)
    slot: Mapped[str] = mapped_column(String(20), index=True)
    laundry: Mapped[str] = mapped_column(String(20), index=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    image_key: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Suggestion(Base, Timestamp):
    __tablename__ = "recognition_suggestions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    garment_id: Mapped[str | None] = mapped_column(
        ForeignKey("garments.id", ondelete="SET NULL"), nullable=True
    )
    image_key: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(30))
    proposed: Mapped[dict] = mapped_column(JSON)
    confirmed: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Outfit(Base, Timestamp):
    __tablename__ = "outfits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    context: Mapped[dict] = mapped_column(JSON)
    scores: Mapped[dict] = mapped_column(JSON)
    snapshots: Mapped[list] = mapped_column(JSON)
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("outfits.id", ondelete="SET NULL"), nullable=True
    )


class OutfitItem(Base):
    __tablename__ = "outfit_items"
    # The composite primary key already guarantees one item per outfit slot.
    outfit_id: Mapped[str] = mapped_column(
        ForeignKey("outfits.id", ondelete="CASCADE"), primary_key=True
    )
    garment_id: Mapped[str | None] = mapped_column(
        ForeignKey("garments.id", ondelete="SET NULL"), nullable=True
    )
    slot: Mapped[str] = mapped_column(String(20), primary_key=True)


class Feedback(Base, Timestamp):
    __tablename__ = "feedback_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    outfit_id: Mapped[str] = mapped_column(
        ForeignKey("outfits.id", ondelete="CASCADE"), index=True
    )
    event: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    features: Mapped[list] = mapped_column(JSON)


class Preference(Base, Timestamp):
    __tablename__ = "preference_states"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    vector: Mapped[list] = mapped_column(JSON, default=lambda: [0.0] * 4)
    count: Mapped[int] = mapped_column(Integer, default=0)


engine = create_engine(
    os.getenv("DATABASE_URL", "sqlite:///./closetwise.db"),
    **(
        {"connect_args": {"check_same_thread": False}}
        if os.getenv("DATABASE_URL", "sqlite:").startswith("sqlite")
        else {}
    ),
)
if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def sqlite_fk(dbapi, _):
        dbapi.execute("PRAGMA foreign_keys=ON")


Session = sessionmaker(engine, expire_on_commit=False)


def session():
    with Session() as s:
        yield s
