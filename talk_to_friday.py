"""Talk to F.R.I.D.A.Y. — OmniBrain Voice & Chat CLI.

Allows immediate conversation with OmniBrain with lady assistant neural voice audio playback.
Zero external pip dependencies (uses built-in Python standard library).
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

API_BASE = "http://localhost:8000"


def play_mp3_windows(mp3_bytes: bytes):
    """Play MP3 audio using Windows PowerShell MediaPlayer asynchronously."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(mp3_bytes)
            tmp_path = f.name

        abs_path = os.path.abspath(tmp_path).replace("\\", "/")
        ps1_path = os.path.join(tempfile.gettempdir(), "play_friday_voice.ps1")
        with open(ps1_path, "w", encoding="utf-8") as ps_f:
            ps_f.write(f"""Add-Type -AssemblyName presentationCore
$player = New-Object System.Windows.Media.MediaPlayer
$player.Open([System.Uri]'{abs_path}')
$player.Play()
Start-Sleep -Seconds 6
$player.Close()
Remove-Item '{abs_path}' -ErrorAction SilentlyContinue
""")

        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", ps1_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"  [Audio playback error: {e}]")


def login() -> str:
    """Authenticate with OmniBrain API and retrieve access token."""
    url = f"{API_BASE}/v1/auth/login"
    data = "username=admin@omnibrain.local&password=OmniBrain@2026".encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res["data"]["access_token"]


def chat(token: str, message: str, voice: str, include_audio: bool = True) -> dict:
    """Send message to /v1/chat endpoint."""
    url = f"{API_BASE}/v1/chat"
    payload = json.dumps({
        "message": message,
        "include_audio": include_audio,
        "voice": voice,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))["data"]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("=" * 60)
    print("🤖  OMNIBRAIN — F.R.I.D.A.Y. VOICE ASSISTANT")
    print("=" * 60)
    print("Connecting to OmniBrain Brain API on http://localhost:8000 ...")

    try:
        token = login()
        print(" Connected and authenticated as admin@omnibrain.local!\n")
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("Please ensure Docker containers are running (docker compose up -d).")
        return

    print("Choose Voice Mode:")
    print("  [1] Auto (Hindi & English Lady Voice) [Default]")
    print("  [2] English Lady Voice (Jenny)")
    print("  [3] Hindi Lady Voice (Swara)")
    print("  [4] Text Only (Muted — No Audio)")
    choice = input("Select [1/2/3/4] (Enter for 1): ").strip()

    is_audio_enabled = choice != "4"
    if choice == "2":
        voice = "en-US-JennyNeural"
        voice_name = "Jenny (English)"
    elif choice == "3":
        voice = "hi-IN-SwaraNeural"
        voice_name = "Swara (Hindi)"
    elif choice == "4":
        voice = "auto"
        voice_name = "Muted (Text Only)"
    else:
        voice = "auto"
        voice_name = "Auto (Hindi / English)"

    print(f"\n Active Mode: {voice_name}")
    print("Tip: Type '/mute' to turn voice off, '/unmute' to turn it back on.")
    print("Type your message below (or 'exit' / 'quit' to end):\n" + "-" * 60)

    while True:
        try:
            user_msg = input("\nYou > ").strip()
            if not user_msg:
                continue
            if user_msg.lower() in ("exit", "quit", "q", "bye"):
                print("\nFriday > Goodbye! Standing by whenever you need me.")
                break
            if user_msg.lower() == "/mute":
                is_audio_enabled = False
                print("\n[🔇 Voice is now MUTED. Friday will respond in text only.]")
                continue
            if user_msg.lower() == "/unmute":
                is_audio_enabled = True
                print("\n[🔊 Voice is now UNMUTED. Friday will speak her responses.]")
                continue

            print("Thinking...", end="\r", flush=True)
            data = chat(token, user_msg, voice, include_audio=is_audio_enabled)

            # Clear status line
            print(" " * 40, end="\r")

            # Print Assistant reply
            reply = data.get("reply", "")
            print(f"\nF.R.I.D.A.Y. > {reply}")

            # Print 5-point report if action was executed
            report = data.get("report")
            if report:
                print("\n" + "·" * 40)
                print("📋 [TASK EXECUTION REPORT]")
                print(f"  • STATUS: {report.get('status')}")
                if report.get("what_was_done"):
                    print("  • WHAT WAS DONE:")
                    for item in report["what_was_done"]:
                        print(f"    - {item}")
                if report.get("important_results"):
                    print("  • IMPORTANT RESULTS:")
                    for item in report["important_results"]:
                        print(f"    - {item}")
                if report.get("any_problems"):
                    print("  • PROBLEMS:")
                    for item in report["any_problems"]:
                        print(f"    - {item}")
                if report.get("actions_requiring_me"):
                    print("  • ACTIONS REQUIRING YOU:")
                    for item in report["actions_requiring_me"]:
                        print(f"    - {item}")
                print("·" * 40)

            # Play audio
            audio_b64 = data.get("audio_base64")
            if audio_b64:
                audio_bytes = base64.b64decode(audio_b64)
                play_mp3_windows(audio_bytes)

        except KeyboardInterrupt:
            print("\nSession ended.")
            break
        except Exception as e:
            print(f"\n[Error: {e}]")


if __name__ == "__main__":
    main()

