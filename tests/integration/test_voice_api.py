"""Integration tests for Voice Studio and Cloning REST API."""
import base64
import io
import math
import struct
import wave
import pytest
from packages.core.security.auth import create_access_token


def generate_sample_wav(freq: float = 160.0) -> bytes:
    sample_rate = 16000
    num_samples = int(sample_rate * 1.0)
    samples = [int(12000 * math.sin(2 * math.pi * freq * i / sample_rate)) for i in range(num_samples)]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{num_samples}h", *samples))
    return buf.getvalue()


@pytest.mark.asyncio
async def test_voice_clone_api_flow(test_client, test_user):
    token = create_access_token(subject=str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Check current voice profile (initial state)
    cur_res = await test_client.get("/v1/voice/clone/current", headers=headers)
    assert cur_res.status_code == 200
    assert "has_profile" in cur_res.json()["data"]

    # 2. Upload sample audio via base64
    wav_bytes = generate_sample_wav(freq=180.0)
    b64_audio = base64.b64encode(wav_bytes).decode("utf-8")

    upload_res = await test_client.post(
        "/v1/voice/clone/upload",
        json={"audio_base64": b64_audio, "filename": "test_sample.wav"},
        headers=headers,
    )
    assert upload_res.status_code == 200
    profile_data = upload_res.json()["data"]["profile"]
    assert profile_data["detected_pitch_hz"] > 0
    assert profile_data["duration_sec"] > 0

    # 3. Test Preview Synthesis with Cloned Voice
    prev_res = await test_client.post(
        "/v1/voice/clone/preview",
        json={"text": "Namaste! Yeh cloned voice ka test audio hai."},
        headers=headers,
    )
    assert prev_res.status_code == 200
    prev_data = prev_res.json()["data"]
    assert len(prev_data["audio_base64"]) > 100

    # 4. Activate Cloned Voice as Default
    act_res = await test_client.post("/v1/voice/clone/activate", headers=headers)
    assert act_res.status_code == 200
    assert act_res.json()["data"]["active_voice"] == "custom_clone"

    # 5. Verify current profile reports active
    verify_res = await test_client.get("/v1/voice/clone/current", headers=headers)
    assert verify_res.status_code == 200
    assert verify_res.json()["data"]["has_profile"] is True
    assert verify_res.json()["data"]["active_voice"] == "custom_clone"

