# blog-autopost

개인 블로그 「내향인의 기록」(Quiet Journals)에 글 초안을 자동으로 올리는 개인용 도구입니다.

미리 정해둔 주제 목록(`topics.csv`)을 바탕으로 Claude API가 글 초안을 쓰고,
사진을 가볍게 가공해 Blogger API로 운영자 본인의 블로그에 **초안**으로 저장합니다.
발행은 운영자가 직접 검토한 뒤 합니다.

## 구성
- `src/` 글 생성, 이미지 가공, Blogger 업로드
- `topics.csv` 작성할 주제 목록
- `.github/workflows/daily-post.yml` 매일 한 번 자동 실행
- `docs/` 소개 · 개인정보처리방침 · 서비스 약관 페이지

## 문의
이 저장소의 Issues 탭을 이용해 주세요.

---

A personal tool that drafts posts with the Claude API and saves them as drafts to the owner's own Blogger blog.
