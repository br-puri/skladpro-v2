"""One-time migration: strip the white padding that a previous square-pad step
baked into every product photo, recovering each image's natural content
bounding box. Detects padding by diffing against a pure-white canvas (with a
small tolerance for compression noise) — this works directly on the current
files, no original/un-padded source needed, and never crops into real content
since it only trims uniform near-white margin from the edges inward.
Keeps the original filename and format — no DB changes needed. Run once,
inside the running container, with `docker exec`.
"""
import os
from PIL import Image, ImageChops

UPLOAD_FOLDER = '/app/static/uploads/products'
WHITE_TOLERANCE = 8  # per-channel difference from pure white still counted as "padding"

SAVE_FORMAT = {
    'jpg': 'JPEG', 'jpeg': 'JPEG',
    'png': 'PNG',
    'webp': 'WEBP',
    'gif': 'PNG',
    'avif': 'WEBP',
}


def trim_white_padding(img):
    rgb = img.convert('RGB')
    bg = Image.new('RGB', rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, bg)
    # Treat small per-channel differences (compression noise) as still-white
    diff = diff.point(lambda p: 0 if p <= WHITE_TOLERANCE else 255)
    bbox = diff.getbbox()
    if bbox is None:
        return img  # fully blank/white image — nothing to trim
    if bbox == (0, 0, img.width, img.height):
        return img  # no padding found
    return img.crop(bbox)


def main():
    files = sorted(os.listdir(UPLOAD_FOLDER))
    print(f"{len(files)} files found")
    done = skipped = failed = 0
    for fname in files:
        path = os.path.join(UPLOAD_FOLDER, fname)
        if not os.path.isfile(path):
            continue
        ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
        fmt = SAVE_FORMAT.get(ext)
        if not fmt:
            print(f"  SKIP {fname} (unrecognized extension)")
            skipped += 1
            continue
        try:
            img = Image.open(path)
            before = img.size
            trimmed = trim_white_padding(img)
            if trimmed.size == before:
                skipped += 1
                continue
            if fmt == 'JPEG':
                trimmed.convert('RGB').save(path, 'JPEG', quality=90, optimize=True)
            elif fmt == 'WEBP':
                trimmed.convert('RGB').save(path, 'WEBP', quality=90, method=4)
            else:
                trimmed.save(path, fmt, optimize=True)
            print(f"  {fname}: {before} -> {trimmed.size}")
            done += 1
        except Exception as e:
            print(f"  FAILED {fname}: {e}")
            failed += 1
    print(f"Done. {done} trimmed, {skipped} already tight/skipped, {failed} failed.")


if __name__ == '__main__':
    main()
