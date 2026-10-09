"""Initial schema. Explicit table definitions keep migration history immutable."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def owner():
    return sa.Column(
        "owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False
    )


def idcol():
    return sa.Column("id", sa.String(36), primary_key=True)


def upgrade():
    op.create_table(
        "users",
        idcol(),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("demo", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "garments",
        idcol(),
        owner(),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("slot", sa.String(20), nullable=False),
        sa.Column("laundry", sa.String(20), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("image_key", sa.String(100)),
        *timestamps(),
    )
    op.create_table(
        "recognition_suggestions",
        idcol(),
        owner(),
        sa.Column(
            "garment_id",
            sa.String(36),
            sa.ForeignKey("garments.id", ondelete="SET NULL"),
        ),
        sa.Column("image_key", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("proposed", sa.JSON(), nullable=False),
        sa.Column("confirmed", sa.JSON()),
        *timestamps(),
    )
    op.create_table(
        "outfits",
        idcol(),
        owner(),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("scores", sa.JSON(), nullable=False),
        sa.Column("snapshots", sa.JSON(), nullable=False),
        sa.Column(
            "parent_id", sa.String(36), sa.ForeignKey("outfits.id", ondelete="SET NULL")
        ),
        *timestamps(),
    )
    op.create_table(
        "outfit_items",
        sa.Column(
            "outfit_id",
            sa.String(36),
            sa.ForeignKey("outfits.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "garment_id",
            sa.String(36),
            sa.ForeignKey("garments.id", ondelete="SET NULL"),
        ),
        sa.Column("slot", sa.String(20), primary_key=True),
        sa.UniqueConstraint("outfit_id", "slot"),
    )
    op.create_table(
        "feedback_events",
        idcol(),
        owner(),
        sa.Column(
            "outfit_id",
            sa.String(36),
            sa.ForeignKey("outfits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(100)),
        sa.Column("features", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "preference_states",
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True
        ),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        *timestamps(),
    )
    for table, columns in {
        "garments": ["owner_id", "slot", "laundry"],
        "recognition_suggestions": ["owner_id"],
        "outfits": ["owner_id"],
        "feedback_events": ["owner_id", "outfit_id"],
    }.items():
        for col in columns:
            op.create_index(f"ix_{table}_{col}", table, [col])


def downgrade():
    for table in [
        "preference_states",
        "feedback_events",
        "outfit_items",
        "outfits",
        "recognition_suggestions",
        "garments",
        "users",
    ]:
        op.drop_table(table)
