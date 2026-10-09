"""Offline CLIP photo classification. No remote inference or runtime downloads."""

import io, os
from pathlib import Path
from functools import lru_cache
from threading import Lock
import numpy as np
from PIL import Image, ImageOps
from .schemas import Attributes

CATALOG = [
    ("a t-shirt", "shirt", "top", 0, 0),
    ("a collared button-up shirt", "shirt", "top", 1, 3),
    ("a blouse", "shirt", "top", 1, 3),
    ("a knitted sweater or cardigan", "knit", "top", 3, 2),
    ("tailored trousers or chinos", "trousers", "bottom", 2, 3),
    ("denim jeans", "jeans", "bottom", 2, 1),
    ("a skirt", "skirt", "bottom", 1, 2),
    ("a dress", "dress", "onepiece", 2, 3),
    ("a jumpsuit", "jumpsuit", "onepiece", 2, 2),
    ("sneakers or trainers", "sneakers", "shoes", 1, 1),
    ("leather loafers", "loafers", "shoes", 1, 3),
    ("lace-up dress shoes", "dress_shoes", "shoes", 1, 3),
    ("boots", "boots", "shoes", 2, 2),
    ("a blazer or light jacket", "jacket", "outerwear", 2, 3),
    ("a thick winter coat", "coat", "outerwear", 4, 3),
    ("a scarf", "scarf", "accessory", 2, 2),
    ("a handbag or tote bag", "bag", "accessory", 0, 2),
]
COLORS = [
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
PATTERNS = ["solid", "striped", "checked", "floral", "graphic"]
LOCK = Lock()


@lru_cache(maxsize=1)
def runtime():
    import onnxruntime as ort
    from tokenizers import Tokenizer

    root = Path(
        os.getenv(
            "LOCAL_MODEL_PATH",
            str(Path(__file__).resolve().parent.parent / "models" / "clip"),
        )
    )
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    model = ort.InferenceSession(
        str(root / "model.onnx"), options, providers=["CPUExecutionProvider"]
    )
    tokenizer = Tokenizer.from_file(str(root / "tokenizer.json"))
    tokenizer.enable_padding(pad_id=49407, pad_token="<|endoftext|>")
    tokenizer.enable_truncation(max_length=77)
    return model, tokenizer


def similarities(image, descriptions):
    model, tokenizer = runtime()
    encodings = tokenizer.encode_batch(["a photo of " + x + "." for x in descriptions])
    inputs = {
        "input_ids": np.asarray([e.ids for e in encodings], dtype=np.int64),
        "attention_mask": np.asarray(
            [e.attention_mask for e in encodings], dtype=np.int64
        ),
        "pixel_values": image,
    }
    output = model.run(
        None,
        {k: v for k, v in inputs.items() if k in {i.name for i in model.get_inputs()}},
    )
    outputs = {item.name: value for item, value in zip(model.get_outputs(), output)}
    return np.asarray(outputs["logits_per_image"])[0]


class LocalProvider:
    name = "local"

    def analyze(self, raw):
        with Image.open(io.BytesIO(raw)) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im = ImageOps.fit(im, (224, 224), method=Image.Resampling.BICUBIC)
            pixels = np.asarray(im, dtype=np.float32) / 255
            pixels = (
                pixels - np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
            ) / np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)
            pixels = pixels.transpose(2, 0, 1)[None]
        with LOCK:
            labels = [c[0] for c in CATALOG] + [
                "food on a plate",
                "an animal",
                "a landscape",
                "an empty room",
            ]
            scores = similarities(pixels, labels)
            index = int(np.argmax(scores))
            if index >= len(CATALOG):
                raise ValueError("No clothing identified")
            description, category, slot, warmth, formality = CATALOG[index]
            color = COLORS[
                int(
                    np.argmax(
                        similarities(
                            pixels, [f"{color} {description}" for color in COLORS]
                        )
                    )
                )
            ]
            pattern = PATTERNS[
                int(
                    np.argmax(
                        similarities(
                            pixels, [f"{pattern} {description}" for pattern in PATTERNS]
                        )
                    )
                )
            ]
        name = f"{color.title()} {category.replace('_', ' ')}"
        attrs = Attributes(
            name=name,
            category=category,
            slot=slot,
            primary_color=color,
            pattern=pattern,
            warmth=warmth,
            formality=formality,
            weather=["dry", "wind"],
            seasons=["spring", "autumn", "winter"]
            if warmth >= 2
            else ["spring", "summer", "autumn"],
            notes="Recognized locally with CLIP. Category, color and pattern are image estimates. Warmth and formality use category defaults. Waterproofing and textile properties are not verified.",
        )
        return (
            attrs,
            "Local image estimates can be wrong. You can edit the garment anytime; warmth and dressiness use category defaults.",
        )
