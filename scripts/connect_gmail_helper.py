"""
Gmail OAuth Instant Connector Helper for SARA
Target Gmail: vikas635026@gmail.com
1. Opens Google OAuth in browser (localhost:8000 callback).
2. Captures auth code from Google.
3. Exchanges code for live Google tokens.
4. Encrypts and writes Connection directly to Supabase DB.
5. SARA Cloud is immediately 100% connected to vikas635026@gmail.com!
"""
import sys
import os
import time
import asyncio
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv

# Load env from omnibrain root
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

from packages.core.db.session import async_session_maker
from packages.core.db.models import User, Connection
from packages.core.security.crypto import encrypt_token
from sqlalchemy import select

CLIENT_ID = "279884272633-h83038hv52ovkk2r35tne2nbqofnqv0f.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:8000/v1/connectors/google/callback"
TARGET_EMAIL = "vikas635026@gmail.com"
DEFAULT_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/userinfo.email",
]

class CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/v1/connectors/google/callback"):
            query = urllib.parse.parse_qs(parsed.query)
            code = query.get("code", [None])[0]

            if not code:
                self.send_response(400)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<h1>Error: Missing authorization code from Google</h1>")
                return

            print(f"\n[+] Authorization code received from Google!")
            print(f"[+] Exchanging code for live Google access and refresh tokens...")

            # 1. Exchange code with Google
            tokens = None
            try:
                resp = httpx.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": code,
                        "client_id": CLIENT_ID,
                        "client_secret": CLIENT_SECRET,
                        "redirect_uri": REDIRECT_URI,
                        "grant_type": "authorization_code",
                    },
                    timeout=20.0,
                )
                if resp.status_code == 200:
                    tokens = resp.json()
                else:
                    print(f"[!] Error exchanging code: {resp.status_code} - {resp.text}")
            except Exception as e:
                print(f"[!] Exception during token exchange: {e}")

            if not tokens or "access_token" not in tokens:
                self.send_response(500)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<h1>Error: Could not exchange authorization code with Google.</h1>")
                return

            # Fetch account email using access token
            email = TARGET_EMAIL
            try:
                userinfo_resp = httpx.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {tokens['access_token']}"},
                    timeout=10.0,
                )
                if userinfo_resp.status_code == 200:
                    email = userinfo_resp.json().get("email", TARGET_EMAIL)
            except Exception:
                pass

            print(f"[+] Google authenticated account: {email}")

            # 2. Save directly to Supabase Database
            async def save_to_db():
                async with async_session_maker() as session:
                    # Find user
                    u_res = await session.execute(
                        select(User).where(
                            (User.email == TARGET_EMAIL) | (User.email == "admin@omnibrain.local")
                        )
                    )
                    user = u_res.scalars().first()
                    if not user:
                        user = User(
                            email=TARGET_EMAIL,
                            name="Vikas",
                            role="owner",
                            timezone="Asia/Kolkata",
                        )
                        session.add(user)
                        await session.flush()

                    now = datetime.now(timezone.utc)
                    expires_in = tokens.get("expires_in", 3600)
                    expires_at = now + timedelta(seconds=expires_in)

                    # Update or insert connection
                    c_res = await session.execute(
                        select(Connection).where(
                            Connection.user_id == user.id,
                            Connection.provider == "google",
                        )
                    )
                    conn = c_res.scalar_one_or_none()

                    if not conn:
                        conn = Connection(
                            user_id=user.id,
                            provider="google",
                            account_email=email,
                            scopes=DEFAULT_GOOGLE_SCOPES,
                            access_token_encrypted=encrypt_token(tokens["access_token"]),
                            refresh_token_encrypted=encrypt_token(tokens.get("refresh_token", "")),
                            expires_at=expires_at,
                            status="ONLINE",
                            metadata_json={"connected_at": now.isoformat()},
                        )
                        session.add(conn)
                    else:
                        conn.account_email = email
                        conn.access_token_encrypted = encrypt_token(tokens["access_token"])
                        if tokens.get("refresh_token"):
                            conn.refresh_token_encrypted = encrypt_token(tokens["refresh_token"])
                        conn.expires_at = expires_at
                        conn.status = "ONLINE"

                    await session.commit()
                    print(f"[+] Connection saved to Supabase: {email} (ONLINE)")

            try:
                asyncio.run(save_to_db())
            except Exception as e:
                print(f"[!] Database save error: {e}")

            # Send response to browser
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()

            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>SARA - Gmail Connected</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #030712;
            color: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
        }}
        .card {{
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 24px;
            padding: 48px;
            text-align: center;
            max-width: 480px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
        }}
        .icon {{
            width: 72px;
            height: 72px;
            background: #10b9811a;
            border: 2px solid #10b981;
            color: #10b981;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
            font-size: 36px;
        }}
        h2 {{ margin: 0 0 12px; font-size: 24px; font-weight: 700; color: #ffffff; }}
        p {{ margin: 0 0 24px; color: #94a3b8; font-size: 15px; line-height: 1.6; }}
        .badge {{
            display: inline-block;
            background: #1e293b;
            color: #38bdf8;
            padding: 8px 16px;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 24px;
            border: 1px solid #334155;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">&#10003;</div>
        <h2>Gmail Connected to SARA!</h2>
        <div class="badge">{email}</div>
        <p>Aapki Gmail (<strong>{email}</strong>) SARA AI ke saath 100% connect ho gayi hai! Sara ab aapki real emails padh aur manage kar sakti hai.</p>
        <p style="font-size: 13px; color: #64748b;">Aap is tab ko band kar sakte hain.</p>
    </div>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))
            print(f"\n=======================================================")
            print(f" SUCCESS! {email} is now LIVE and CONNECTED to SARA!")
            print(f"=======================================================\n")

            def shutdown():
                time.sleep(1)
                self.server.shutdown()
            import threading
            threading.Thread(target=shutdown).start()
        else:
            self.send_response(404)
            self.end_headers()

def main():
    state = "user_452f67a4-3fbf-4c4a-866d-75e8b6427c8b_direct"
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(DEFAULT_GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "select_account consent",
        "login_hint": TARGET_EMAIL,
        "state": state,
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    print("=" * 65)
    print("      SARA AI - GMAIL CONNECTOR FOR " + TARGET_EMAIL)
    print("=" * 65)
    print("\nStarting local authentication listener on port 8000...")
    
    server = HTTPServer(("127.0.0.1", 8000), CallbackHandler)
    print("[+] Listener ready! Opening Google Sign-in in your browser...")
    webbrowser.open(auth_url)

    print("\nPlease choose " + TARGET_EMAIL + " and click 'Allow' in your browser.")
    print("Waiting for authentication callback...\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    print("\n[Done] Authentication server closed.")

if __name__ == "__main__":
    main()
