"""사진을 플랫폼마다 다른 파일이 되도록 살짝 가공한다 (랜덤 크롭 + 리사이즈 + EXIF 제거)."""
import random
from pathlib import Path

from PIL import Image, ImageOps

EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_WIDTH = 1200


def process_images(src_dir: Path, out_dir: Path) -> list[Path]:
    if not src_dir.is_dir():
        return []
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(p for p in src_dir.iterdir() if p.suffix.lower() in EXTS)
    results = []
    for i, src in enumerate(sources, 1):
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")  # 회전 정보 반영 후 EXIF 버림
            w, h = im.size
            ratio = random.uniform(0.03, 0.06)  # 가장자리 3~6% 크롭
            dx, dy = int(w * ratio / 2), int(h * ratio / 2)
            im = im.crop((dx, dy, w - dx, h - dy))
            if im.width > MAX_WIDTH:
                im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)), Image.LANCZOS)
            out = out_dir / f"{i:02d}.jpg"
            im.save(out, "JPEG", quality=85, optimize=True)
        results.append(out)
    return results
