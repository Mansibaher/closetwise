"""Download pinned free model assets once; inference stays offline."""

from pathlib import Path
import httpx

root = Path(__file__).resolve().parents[1] / "models" / "clip"
root.mkdir(parents=True, exist_ok=True)
revision = "d15189d7028b43f1d3e65039190477f6af591c2a"
for file in ["onnx/model.onnx", "tokenizer.json", "preprocessor_config.json"]:
    target = root / Path(file).name
    if target.exists():
        continue
    partial = target.with_suffix(target.suffix + ".download")
    with httpx.stream(
        "GET",
        f"https://huggingface.co/Xenova/clip-vit-base-patch32/resolve/{revision}/{file}",
        follow_redirects=True,
        timeout=180,
    ) as response:
        response.raise_for_status()
        with partial.open("wb") as out:
            for chunk in response.iter_bytes():
                out.write(chunk)
    partial.replace(target)
    print("Downloaded", target.name)
print("Ready. Set RECOGNITION_PROVIDER=local before starting the backend.")
