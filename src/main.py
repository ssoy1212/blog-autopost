"""topics.csv에서 다음 주제를 골라 글 생성 → 이미지 가공/호스팅 → Blogger 업로드."""
import csv
import html as htmllib
import os
import re
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from generate import generate_post, suggest_topic
from images import process_images

ROOT = Path(__file__).resolve().parent.parent
TOPICS = ROOT / "topics.csv"
CATEGORIES = ROOT / "categories.csv"
FEEDS = ROOT / "feeds.txt"
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


def pick_category(rows):
    """categories.csv의 weight만큼 순서표를 펼쳐 놓고, 자동 생성한 글 수만큼 돌려가며 고른다."""
    if not CATEGORIES.exists():
        return None
    with CATEGORIES.open(encoding="utf-8", newline="") as f:
        cats = [c for c in csv.DictReader(f) if (c.get("category") or "").strip()]
    schedule = []
    for c in cats:
        schedule += [c] * max(1, int((c.get("weight") or "1").strip() or 1))
    if not schedule:
        return None
    auto_count = sum(1 for r in rows if (r.get("category") or "").strip())
    return schedule[auto_count % len(schedule)]


def recent_titles(per_feed: int = 8, limit: int = 40) -> list[str]:
    """feeds.txt의 RSS/Atom 주소에서 최근 글 제목을 읽는다. 실패한 피드는 건너뛴다."""
    if not FEEDS.exists():
        return []
    titles = []
    for line in FEEDS.read_text(encoding="utf-8").splitlines():
        url = line.strip()
        if not url or url.startswith("#") or not url.startswith(("http://", "https://")):
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "blog-autopost/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                root = ET.fromstring(resp.read(2_000_000))
            found = [(el.findtext("title") or "").strip() for el in root.iter("item")]
            if not found:  # Atom
                found = [(el.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
                         for el in root.iter("{http://www.w3.org/2005/Atom}entry")]
            titles += [t[:80] for t in found if t][:per_feed]
        except Exception as e:
            print(f"[피드 건너뜀] {url}: {e}")
    return titles[:limit]


def auto_topic(fields, rows):
    """처리할 주제가 없을 때 카테고리를 골라 Claude가 새 주제를 정해 topics.csv 행으로 만든다."""
    cat = pick_category(rows)
    if cat is None:
        return None
    existing = [r["topic"] for r in rows if r.get("topic")]
    recent = recent_titles()
    print(f"[참고 피드] 최근 글 제목 {len(recent)}개")
    sug = suggest_topic(cat["category"].strip(), (cat.get("description") or "").strip(), existing, recent)
    if "category" not in fields:
        fields = [*fields, "category"]
    nums = [int(r["id"]) for r in rows if (r.get("id") or "").strip().isdigit()]
    row = {k: "" for k in fields}
    row.update(id=f"{max(nums, default=0) + 1:03d}", topic=sug["topic"],
               keywords=sug["keywords"], category=cat["category"].strip())
    rows.append(row)
    print(f"[자동 주제] ({row['category']}) {row['topic']}")
    return {"kind": "topic", "fields": fields, "rows": rows, "row": row, "pid": row["id"]}


def insert_images(body: str, urls: list[str], alt: str) -> str:
    for i, url in enumerate(urls, 1):
        tag = (
            f'<img src="{url}" alt="{htmllib.escape(alt)} {i}" loading="lazy" '
            'style="max-width:100%;height:auto;">'
        )
        body = body.replace(f"[[IMG{i}]]", tag)
    return re.sub(r"\[\[IMG\d+\]\]", "", body)  # 남은 자리표시자 제거


def next_job():
    """방문기(posts/) 중 아직 안 올린 것을 먼저, 없으면 topics.csv의 다음 주제."""
    posts = ROOT / "posts"
    if posts.is_dir():
        for d in sorted(x for x in posts.iterdir() if x.is_dir()):
            if (d / "info.md").exists() and not (d / "status.txt").exists():
                return {"kind": "review", "dir": d, "pid": d.name}
    fields, rows = load_topics()
    row = next((r for r in rows if not (r.get("status") or "").strip()), None)
    if row:
        return {"kind": "topic", "fields": fields, "rows": rows, "row": row, "pid": row["id"].strip()}
    return auto_topic(fields, rows)


def main():
    job = next_job()
    if job is None:
        print("남은 글감이 없고 categories.csv도 없습니다. posts/에 방문기를 넣거나 topics.csv·categories.csv를 채우세요.")
        return
    pid = job["pid"]

    if job["kind"] == "review":
        from review import generate_review, parse_info
        info = parse_info(job["dir"] / "info.md")
        images = process_images(job["dir"], ROOT / "public" / pid)
        print(f"[방문기 {pid}] {info.get('이름', '')} / 이미지 {len(images)}장")
        post = generate_review(info, len(images))
    else:
        row = job["row"]
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

    status = f"{'draft' if DRAFT else 'published'}:{result.get('id')}"
    if job["kind"] == "review":
        done_file = job["dir"] / "status.txt"
        done_file.write_text(status + "\n", encoding="utf-8")
        changed = str(done_file.relative_to(ROOT))
    else:
        job["row"]["status"] = status
        save_topics(job["fields"], job["rows"])
        changed = "topics.csv"
    if REPO:
        git("add", changed)
        git("commit", "-m", f"done {pid}")
        git("push")


if __name__ == "__main__":
    main()
