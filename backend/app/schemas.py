from typing import Literal
from pydantic import BaseModel, Field, model_validator, ConfigDict

Slot = Literal["top", "bottom", "shoes", "onepiece", "outerwear", "accessory"]
Color = Literal[
    "black",
    "white",
    "navy",
    "gray",
    "beige",
    "brown",
    "blue",
    "green",
    "red",
    "pink",
    "purple",
    "yellow",
]


class Attributes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    category: Literal[
        "shirt",
        "knit",
        "trousers",
        "skirt",
        "jeans",
        "dress",
        "jumpsuit",
        "sneakers",
        "loafers",
        "dress_shoes",
        "boots",
        "coat",
        "jacket",
        "scarf",
        "bag",
    ]
    slot: Slot
    audience: Literal["men", "women", "unisex"] = "unisex"
    primary_color: Color
    secondary_color: Color | None = None
    pattern: Literal["solid", "striped", "checked", "floral", "graphic"] = "solid"
    warmth: int = Field(ge=0, le=4)
    formality: int = Field(ge=0, le=4)
    seasons: list[Literal["spring", "summer", "autumn", "winter"]] = Field(
        default_factory=lambda: ["spring", "autumn"], max_length=4
    )
    weather: list[Literal["dry", "rain", "wind"]] = Field(
        default_factory=lambda: ["dry"], max_length=3
    )
    tags: list[str] = Field(default_factory=list, max_length=12)
    laundry: Literal["clean", "dirty", "unavailable"] = "clean"
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def compatible(self):
        mapping = {
            "shirt": "top",
            "knit": "top",
            "trousers": "bottom",
            "skirt": "bottom",
            "jeans": "bottom",
            "dress": "onepiece",
            "jumpsuit": "onepiece",
            "sneakers": "shoes",
            "loafers": "shoes",
            "dress_shoes": "shoes",
            "boots": "shoes",
            "coat": "outerwear",
            "jacket": "outerwear",
            "scarf": "accessory",
            "bag": "accessory",
        }
        if mapping[self.category] != self.slot:
            raise ValueError("Category and outfit slot must agree")
        if any(len(x) > 40 for x in self.tags):
            raise ValueError("Tags must be at most 40 characters")
        return self


class GarmentInput(Attributes):
    suggestion_id: str | None = None


class GarmentView(Attributes):
    id: str
    archived: bool
    image_url: str | None
    thumbnail_url: str | None


class Credentials(BaseModel):
    email: str = Field(
        min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    password: str = Field(min_length=8, max_length=128)


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(default="", max_length=80)
    outfit_style: Literal["men", "women", "all"] = "all"
    default_occasion: Literal["job interview", "everyday", "dinner", "weekend"] = (
        "job interview"
    )


class UserView(BaseModel):
    id: str
    email: str
    demo: bool
    profile: Profile = Field(default_factory=Profile)


class Context(BaseModel):
    model_config = ConfigDict(extra="forbid")
    occasion: str = Field(default="job interview", max_length=80)
    temperature: float = Field(default=12, ge=-10, le=40)
    precipitation: Literal["dry", "rain"] = "dry"
    wind: float = Field(default=8, ge=0, le=100)
    min_formality: int = Field(default=2, ge=0, le=4)
    max_formality: int = Field(default=4, ge=0, le=4)
    required: list[str] = Field(default_factory=list, max_length=6)
    excluded: list[str] = Field(default_factory=list, max_length=500)
    outerwear: bool = True
    accessory: bool = False

    @model_validator(mode="after")
    def bounds(self):
        if self.min_formality > self.max_formality:
            raise ValueError("Minimum must not exceed maximum formality")
        if len(set(self.required)) != len(self.required):
            raise ValueError("Duplicate required IDs")
        return self


class ScoreView(BaseModel):
    color: float
    coherence: float
    comfort: float
    personal: float
    novelty: float
    rotation: float
    total: float


class OutfitView(BaseModel):
    id: str
    context: Context
    garments: list[GarmentView]
    scores: ScoreView
    explanations: list[str]
    parent_id: str | None


class GenerateView(BaseModel):
    outfits: list[OutfitView]
    candidate_count: int
    approximate: bool = True


class AdjustmentInput(BaseModel):
    direction: Literal["warmer", "cooler", "casual", "formal"]


class AdjustmentView(BaseModel):
    outfit: OutfitView
    original_id: str
    replacement_id: str
    direction: str
    explanation: str


class FeedbackInput(BaseModel):
    event: Literal["wore", "liked", "disliked", "skipped"]
    reason: (
        Literal[
            "too formal", "too casual", "too cold", "too warm", "don’t like the colors"
        ]
        | None
    ) = None


class FeedbackView(BaseModel):
    id: str
    outfit_id: str
    event: str
    reason: str | None
    created_at: str


class InsightsView(BaseModel):
    vector: list[float]
    count: int
    feature_names: list[str]
    explanation: str


class AnalysisView(BaseModel):
    id: str
    provider: str
    proposed: Attributes
    uncertainty: str | None
    warning: str | None
    image_url: str


class ArchiveInput(BaseModel):
    archived: bool
