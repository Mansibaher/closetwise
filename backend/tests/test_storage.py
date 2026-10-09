import io
import pytest
from PIL import Image
from app.storage import normalize, safe_key


@pytest.mark.parametrize("size", [(30, 100), (6001, 100), (5000, 5000)])
def test_dimension_limits(size):
    im = Image.new("RGB", size)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    with pytest.raises(ValueError):
        normalize(buf.getvalue())


def test_orientation_and_thumbnail():
    im = Image.new("RGB", (300, 500))
    exif = im.getexif()
    exif[274] = 6
    exif[270] = "private metadata"
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif)
    full, thumb = normalize(buf.getvalue())
    decoded = Image.open(io.BytesIO(full))
    assert decoded.size == (500, 300) and not decoded.getexif()
    assert max(Image.open(io.BytesIO(thumb)).size) <= 400


def test_size_and_traversal():
    with pytest.raises(ValueError):
        normalize(b"x" * (8 * 1024 * 1024 + 1))
    with pytest.raises(ValueError):
        safe_key("../secret.webp")


def test_iphone_heic_converts_to_private_webp():
    from pillow_heif import from_pillow
    image = Image.new("RGB", (240, 320), "blue")
    exif=image.getexif(); exif[270]="Private photo metadata"; image.info["exif"]=exif.tobytes()
    original=io.BytesIO()
    from_pillow(image).save(original,quality=85)
    full,thumb=normalize(original.getvalue())
    decoded=Image.open(io.BytesIO(full))
    assert decoded.format=="WEBP" and decoded.size==(240,320)
    assert not decoded.getexif()
    assert max(Image.open(io.BytesIO(thumb)).size)<=400


@pytest.mark.parametrize("format", ["AVIF", "GIF", "BMP", "TIFF"])
def test_other_gallery_formats_become_static_webp(format):
    image=Image.new("RGB", (240,320), "blue")
    encoded=io.BytesIO(); image.save(encoded,format)
    full,thumb=normalize(encoded.getvalue())
    decoded=Image.open(io.BytesIO(full))
    assert decoded.format=="WEBP" and decoded.size==(240,320)
    assert not decoded.getexif()
    assert max(Image.open(io.BytesIO(thumb)).size)<=400
