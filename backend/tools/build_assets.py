from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.seed import LEGACY_DATA as DATA, illustration

root = Path(__file__).resolve().parents[1] / "assets"
root.mkdir(exist_ok=True)
for i, (name, category, slot, color, warmth, formality) in enumerate(DATA):
    pattern = (
        "striped" if "Striped" in name else "floral" if "Floral" in name else "solid"
    )
    (root / f"{i:02}.png").write_bytes(illustration(slot, color, pattern))
print(f"Created {len(DATA)} original images in {root}")
