"""posts/<폴더>/info.md 양식(카페·식당 방문기)을 읽어 글을 만든다.
정보 박스는 적힌 값을 그대로 표로 넣고, Claude는 본문만 쓴다."""
import html as htmllib
from pathlib import Path

from generate import call_claude

INFO_KEYS = ["위치", "가는 길", "영업시간", "웨이팅", "주문한 메뉴", "주차", "좌석·콘센트·와이파이"]

REVIEW_SYSTEM = """너는 블로그 「내향인의 기록」의 작가이고, 운영자가 직접 다녀온 {kind} 방문 메모를 블로그 후기로 정리한다.
- 운영자 본인의 1인칭 경험담. 차분하고 친근한 존댓말. 본문은 공백 포함 1500~2500자.
- 메모에 적힌 사실만 쓴다. 메모에 없는 메뉴, 가격, 맛, 위치, 영업시간, 서비스, 사람에 대한 내용은 절대 지어내지 않는다.
  메모가 짧으면 글도 짧게 쓰고, 일반적인 감상으로 분량을 채우지 않는다.
- 상단 정보 박스는 따로 붙으니 본문에서 주소·영업시간을 다시 나열하지 않는다.
- HTML 조각으로 작성. h1, html, head, body 태그와 style 속성 금지.
  사용 가능한 태그: h2, h3, p, ul, li, strong, em, blockquote, div, table, tr, th, td.

[구성]
1. 도입 문단 1~2개 (왜 가게 됐는지, 첫인상 — 메모에 있을 때만)
2. h2 소제목 3~5개. 메모에 내용이 있는 것만: 분위기와 공간 / 주문한 메뉴와 맛 / 좋았던 점과 아쉬운 점 / 이런 분께 추천
   - 좋았던 점과 아쉬운 점이 둘 다 있으면 표로: <table class="qj-table"><tr><th>좋았던 점</th><th>아쉬운 점</th></tr><tr><td>…</td><td>…</td></tr></table>
3. 한줄평이 있으면 blockquote로 그대로 살려서 넣는다.
4. 방문 팁이 메모에서 나오면 <div class="qj-tip"><p><strong>TIP</strong>…</p></div> 1개.
5. 마지막: <div class="qj-checklist"><p class="qj-label">방문 전 체크</p><ul><li>…</li></ul></div> (메모 기반 항목 2~4개)

- 반드시 아래 형식의 JSON 객체 하나만 출력한다. 앞뒤 설명이나 코드펜스 금지.
{{"title": "60자 이내 제목 (가게 이름과 동네 포함)", "labels": ["라벨1", "라벨2", "라벨3"], "html": "<p>...</p>"}}"""


PHOTO_SLOT_NOTE = """사진은 운영자가 나중에 직접 넣는다. 사진이 들어갈 자리 4~5곳에 아래 표시를 넣어라.
- 정보 박스 바로 뒤 첫 자리: 대표 사진 (외관이나 가장 인상적인 장면)
- 분위기·공간 섹션: 1~2자리 (내부, 좌석)
- 메뉴·맛 섹션: 주문한 메뉴마다 1자리
형식: <div class="qj-photo-slot"><p>📷 사진 자리 · 매장 외관</p></div>  (· 뒤에 어떤 사진인지 짧게)
대표 사진 자리는 본문 맨 앞, 도입 문단보다 먼저 둔다."""


def parse_info(path: Path) -> dict:
    data, key = {}, None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        head, sep, rest = line.partition(":")
        if (sep and head.strip() and len(head.strip()) <= 20 and not any(c.isdigit() for c in head)
                and not raw.startswith((" ", "\t", "-"))):
            key = head.strip()
            data[key] = rest.strip()
        elif key:
            data[key] = (data[key] + "\n" + line.strip()).strip()
    return {k: v for k, v in data.items() if v}


def info_box(info: dict) -> str:
    kind = info.get("종류", "장소")
    rows = []
    for k in INFO_KEYS:
        if k in info:
            v = htmllib.escape(info[k]).replace("\n", "<br>")
            rows.append(f"<tr><th>{k}</th><td>{v}</td></tr>")
    name = htmllib.escape(info.get("이름", ""))
    label = f"{kind} 정보" + (f" · {name}" if name else "")
    table = f'<table class="qj-table">{"".join(rows)}</table>' if rows else ""
    return f'<div class="qj-summary"><p class="qj-label">{label}</p>{table}</div>'


def generate_review(info: dict, n_images: int) -> dict:
    kind = info.get("종류", "장소")
    memo = "\n".join(f"{k}: {v}" for k, v in info.items())
    if n_images:
        img_note = (f"본문의 적절한 위치에 [[IMG1]]부터 [[IMG{n_images}]]까지 이미지 자리표시자를 "
                    "각각 정확히 한 번씩, 단독 <p> 태그 안에 넣어라. 사진 순서는 방문 흐름 순서다.")
    else:
        img_note = PHOTO_SLOT_NOTE
    post = call_claude(REVIEW_SYSTEM.format(kind=kind), f"[방문 메모]\n{memo}\n\n{img_note}")
    post["html"] = info_box(info) + post["html"]
    if kind not in post["labels"]:
        post["labels"] = [kind] + post["labels"]
    return post
