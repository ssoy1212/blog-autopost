"""로컬에서 한 번만 실행: 브라우저로 구글 로그인 → refresh token 출력.
사전 준비: Google Cloud 콘솔에서 받은 OAuth 클라이언트(데스크톱 앱) JSON을 client_secret.json으로 저장."""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/blogger"]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
print("\nGOOGLE_REFRESH_TOKEN =", creds.refresh_token)
print("GOOGLE_CLIENT_ID     =", creds.client_id)
print("GOOGLE_CLIENT_SECRET =", creds.client_secret)
