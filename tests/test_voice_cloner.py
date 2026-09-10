"""Unit tests for VoiceCloner acoustic analysis and profile management."""
import io
import math
import struct
import wave
import pytest
from pathlib import Path
from packages.core.voice.cloner import VoiceCloner, VoiceProfile


def create_synthetic_wav(freq_hz: float = 180.0, duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate a clean synthetic sine wave PCM audio stream."""
    num_samples = int(sample_rate * duration_sec)
    samples = []
    for i in range(num_samples):
        # 16-bit sine wave
        val = int(16000 * math.sin(2 * math.pi * freq_hz * i / sample_rate))
        samples.append(val)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{num_samples}h", *samples))

    return buf.getvalue()


def test_voice_cloner_pcm_analysis():
    cloner = VoiceCloner()
    # Test male pitch ~120Hz
    male_wav = create_synthetic_wav(freq_hz=120.0, duration_sec=1.0)
    male_analysis = cloner.analyze_pcm_audio(male_wav[44:], sample_rate=16000)
    assert male_analysis["duration_sec"] > 0
    assert "Male" in male_analysis["tonal_profile"] or male_analysis["pitch_hz"] < 165.0
    assert male_analysis["pitch_adj"].endswith("Hz")

    # Test female pitch ~210Hz
    female_wav = create_synthetic_wav(freq_hz=210.0, duration_sec=1.0)
    female_analysis = cloner.analyze_pcm_audio(female_wav[44:], sample_rate=16000)
    assert female_analysis["pitch_hz"] > 165.0
    assert "Female" in female_analysis["tonal_profile"] or "Bright" in female_analysis["tonal_profile"]


def test_voice_cloner_process_and_save(tmp_path: Path):
    cloner = VoiceCloner(data_dir=tmp_path)
    sample_wav = create_synthetic_wav(freq_hz=175.0, duration_sec=1.5)

    profile = cloner.process_and_save_sample(sample_wav, filename="test_voice.wav")
    assert profile.duration_sec > 1.0
    assert profile.detected_pitch_hz > 0
    assert cloner.profile_path.exists()
    assert cloner.audio_path.exists()

    loaded = cloner.get_current_profile()
    assert loaded is not None
    assert loaded.profile_id == profile.profile_id
    assert loaded.tonal_profile == profile.tonal_profile

