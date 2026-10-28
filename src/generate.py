"""Claude API로 블로그 글(제목/라벨/HTML 본문)을 생성한다."""
import json
import os
import re

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")

SYSTEM = """너는 한국 독자를 대상으로 글을 쓰는 블로그 작가다.
- 친근하지만 정보 위주의 문체로, 본문은 공백 포함 2000~3000자 분량.
- 본문은 HTML 조각으로 작성한다. 사용 가능한 태그: h2, h3, p, ul, ol, li, strong, em, blockquote.
  h1, html, head, body 태그와 인라인 스타일은 쓰지 않는다.
- 확실하지 않은 수치, 통계, 가격, 인용은 지어내지 않는다. 모르면 일반적인 설명으로 대신한다.
- 반드시 아래 형식의 JSON 객체 하나만 출력한다. 앞뒤 설명이나 코드펜스 금지.
{"title": "60자 이내 제목", "labels": ["라벨1", "라벨2", "라벨3"], "html": "<h2>...</h2><p>...</p>"}"""


def generate_post(topic: str, keywords: str, n_images: int) -> dict:
    if n_images:
        img_note = (
            f"본문의 적절한 위치에 [[IMG1]]부터 [[IMG{n_images}]]까지 이미지 자리표시자를 "
            "각각 정확히 한 번씩, 단독 <p> 태그 안에 넣어라."
        )
    else:
        img_note = "이미지 자리표시자는 넣지 마라."

    user = f"주제: {topic}\n핵심 키워드: {keywords}\n{img_note}"

    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용
    msg = client.messages.create(
        model=MODEL,
        max_tokens=6000,
        system=SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()

    data = json.loads(text)
    for key in ("title", "labels", "html"):
        if key not in data:
            raise ValueError(f"응답에 '{key}' 필드가 없습니다: {text[:200]}")
    return data
