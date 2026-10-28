"""Blogger API v3로 글을 올린다. 갱신 토큰(refresh token)으로 매번 자동 인증."""
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/blogger"]


def _service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    return build("blogger", "v3", credentials=creds, cache_discovery=False)


def insert_post(title: str, html: str, labels: list[str], draft: bool = True) -> dict:
    body = {"title": title, "content": html, "labels": labels}
    return (
        _service()
        .posts()
        .insert(blogId=os.environ["BLOGGER_BLOG_ID"], body=body, isDraft=draft)
        .execute()
    )
