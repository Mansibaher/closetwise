import io, os, re, warnings
from pathlib import Path
from uuid import uuid4
from typing import Protocol
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener()


class Storage(Protocol):
    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


def safe_key(key):
    if not re.fullmatch(r"[a-f0-9-]+(?:-thumb)?\.webp", key):
        raise ValueError("Invalid storage key")
    return key


class LocalStorage:
    def __init__(self):
        self.root = Path(os.getenv("STORAGE_PATH", "./data/images"))
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key, data):
        (self.root / safe_key(key)).write_bytes(data)

    def get(self, key):
        return (self.root / safe_key(key)).read_bytes()

    def delete(self, key):
        (self.root / safe_key(key)).unlink(missing_ok=True)


class S3Storage:
    def __init__(self):
        import boto3

        self.client = boto3.client("s3", endpoint_url=os.getenv("S3_ENDPOINT_URL"))
        self.bucket = os.environ["S3_BUCKET"]

    def put(self, key, data):
        self.client.put_object(
            Bucket=self.bucket, Key=safe_key(key), Body=data, ContentType="image/webp"
        )

    def get(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=safe_key(key))[
            "Body"
        ].read()

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=safe_key(key))


def storage():
    return S3Storage() if os.getenv("STORAGE_BACKEND") == "s3" else LocalStorage()


def normalize(data: bytes):
    if not data or len(data) > 8 * 1024 * 1024:
        raise ValueError("Upload must be between 1 byte and 8 MiB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as im:
                if im.format not in ("JPEG", "PNG", "WEBP", "HEIF", "AVIF", "GIF", "BMP", "TIFF"):
                    raise ValueError("Photo format not supported. Choose a standard photo, such as JPEG, PNG, HEIC or AVIF.")
                if (
                    im.width < 64
                    or im.height < 64
                    or im.width > 6000
                    or im.height > 6000
                    or im.width * im.height > 24_000_000
                ):
                    raise ValueError(
                        "Dimensions must be 64–6000 pixels, at most 24 megapixels"
                    )
                im.load()
                clean = ImageOps.exif_transpose(im).convert("RGB")
                clean.thumbnail((1600, 1600))
                clean.info.clear()
                out = io.BytesIO()
                clean.save(out, "WEBP", quality=88)
                clean.thumbnail((400, 400))
                thumb = io.BytesIO()
                clean.save(thumb, "WEBP", quality=82)
                return out.getvalue(), thumb.getvalue()
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as e:
        raise ValueError("Cannot safely decode this image") from e


def save_image(data):
    full, thumb = normalize(data)
    key = f"{uuid4()}.webp"
    store = storage()
    store.put(key, full)
    store.put(key.replace(".webp", "-thumb.webp"), thumb)
    return key
