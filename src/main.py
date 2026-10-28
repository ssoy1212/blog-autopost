"""topics.csv에서 다음 주제를 골라 글 생성 → 이미지 가공/호스팅 → Blogger 업로드."""
import csv
import html as htmllib
import os
import re
import subprocess
from pathlib import Path

from generate import generate_post
from images import process_images

ROOT = Path(__file__).resolve().parent.parent
TOPICS = ROOT / "topics.csv"
REPO = os.environ.get("GITHUB_REPOSITORY")  # Actions에서 자동으로 "owner/repo"가 들어옴
DRY_RUN = os.environ.get("DRY_RUN") == "1"  # 1이면 업로드 없이 preview.html만 생성
DRAFT = os.environ.get("PUBLISH_MODE", "draft") != "publish"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def load_topics():
    with TOPICS.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def save_topics(fields, rows):
    with TOPICS.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def insert_images(body: str, urls: list[str], alt: str) -> str:
    for i, url in enumerate(urls, 1):
        tag = (
            f'<img src="{url}" alt="{htmllib.escape(alt)} {i}" loading="lazy" '
            'style="max-width:100%;height:auto;">'
        )
        body = body.replace(f"[[IMG{i}]]", tag)
    return re.sub(r"\[\[IMG\d+\]\]", "", body)  # 남은 자리표시자 제거


def main():
    fields, rows = load_topics()
    row = next((r for r in rows if not (r.get("status") or "").strip()), None)
    if row is None:
        print("남은 주제가 없습니다. topics.csv에 주제를 추가하세요.")
        return

    pid = row["id"].strip()
    image_dir = (row.get("image_dir") or "").strip()
    images = (
        process_images(ROOT / "images" / image_dir, ROOT / "public" / pid)
        if image_dir
        else []
    )
    print(f"[{pid}] {row['topic']} / 이미지 {len(images)}장")

    post = generate_post(row["topic"], row.get("keywords", ""), len(images))

    if DRY_RUN:
        urls = [str(p.relative_to(ROOT)) for p in images]
        preview = f"<h1>{htmllib.escape(post['title'])}</h1>\n"
        preview += insert_images(post["html"], urls, post["title"])
        (ROOT / "preview.html").write_text(preview, encoding="utf-8")
        print("DRY_RUN: preview.html 생성 완료 (업로드 안 함)")
        return

    from blogger import insert_post  # DRY_RUN에선 구글 라이브러리 불필요

    urls = []
    if images:
        if not REPO:
            raise RuntimeError("GITHUB_REPOSITORY가 없습니다. 로컬 실행이면 DRY_RUN=1을 쓰세요.")
        git("add", f"public/{pid}")
        git("commit", "-m", f"images for {pid}")
        git("push")
        sha = git("rev-parse", "HEAD")  # 커밋 SHA로 고정해 CDN 캐시 문제 회피
        urls = [f"https://cdn.jsdelivr.net/gh/{REPO}@{sha}/public/{pid}/{p.name}" for p in images]

    body = insert_images(post["html"], urls, post["title"])
    result = insert_post(post["title"], body, post["labels"], draft=DRAFT)
    print(f"업로드 완료 ({'초안' if DRAFT else '발행'}): {result.get('title')} / id={result.get('id')}")

    row["status"] = f"{'draft' if DRAFT else 'published'}:{result.get('id')}"
    save_topics(fields, rows)
    if REPO:
        git("add", "topics.csv")
        git("commit", "-m", f"done {pid}")
        git("push")


if __name__ == "__main__":
    main()
