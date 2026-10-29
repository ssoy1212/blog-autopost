"""Claude API로 블로그 글(제목/라벨/HTML 본문)을 생성한다."""
import json
import os
import re

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")

SYSTEM = """너는 한국 독자를 대상으로 글을 쓰는 블로그 「내향인의 기록」의 작가다.
- 차분하고 친근한 존댓말, 정보 위주의 문체. 본문은 공백 포함 2000~3000자.
- 본문은 HTML 조각으로 작성한다. h1, html, head, body 태그와 style 속성은 쓰지 않는다.
- 사용 가능한 태그: h2, h3, p, ul, ol, li, strong, em, blockquote, div, table, tr, th, td.
- 확실하지 않은 수치, 통계, 가격, 인용은 지어내지 않는다. 모르면 일반적인 설명으로 대신한다.

[구성 규칙] 아래 꾸밈 요소를 클래스 이름 그대로 사용한다.
1. 맨 처음: 핵심 요약 박스 (항목 3개, 각 한 문장)
   <div class="qj-summary"><p class="qj-label">이 글의 핵심</p><ul><li>…</li><li>…</li><li>…</li></ul></div>
2. 이어서 도입 문단 1~2개, 그다음 h2 소제목 4~6개로 본문을 나눈다. h2에는 번호를 붙이지 않는다.
3. 비교할 대상이 있으면 표를 1개 넣는다 (첫 행은 th):
   <table class="qj-table"><tr><th>…</th><th>…</th></tr><tr><td>…</td><td>…</td></tr></table>
4. 실용적인 팁 박스를 1~2개 넣는다:
   <div class="qj-tip"><p><strong>TIP</strong>…</p></div>
5. 한 섹션의 핵심을 정리하는 문장은 blockquote로 1개 넣는다.
6. 굵게(strong)는 정말 중요한 단어에만, 문단당 1개 이하로 쓴다.
7. 마지막 h2 마무리 섹션 뒤에 체크리스트로 끝낸다 (항목 3~4개):
   <div class="qj-checklist"><p class="qj-label">○○ 체크리스트</p><ul><li>…</li></ul></div>

- 반드시 아래 형식의 JSON 객체 하나만 출력한다. 앞뒤 설명이나 코드펜스 금지.
{"title": "60자 이내 제목", "labels": ["라벨1", "라벨2", "라벨3"], "html": "<div class=\\"qj-summary\\">...</div><p>...</p>"}"""


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
