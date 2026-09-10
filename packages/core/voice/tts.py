"""Lady Assistant Voice Engine for OmniBrain.

Generates realistic neural text-to-speech audio using edge-tts (100% Free, Zero-Cost).
"""
import base64
import io
import re
from typing import Optional
import edge_tts

DEFAULT_LADY_VOICE = "en-US-JennyNeural"
DEFAULT_HINGLISH_VOICE = "hi-IN-SwaraNeural"


def clean_text_for_speech(text: str) -> str:
    """Normalize text so TTS pronounces words naturally instead of spelling them out."""
    if not text:
        return ""
    # Replace S.A.R.A. or variations with natural word 'Sara'
    cleaned = re.sub(r"(?i)s\.a\.r\.a\.?", "Sara", text)
    cleaned = re.sub(r"\bSARA\b", "Sara", cleaned)
    cleaned = re.sub(r"(?i)f\.r\.i\.d\.a\.y\.?", "Sara", cleaned)
    cleaned = re.sub(r"\bFRIDAY\b", "Sara", cleaned)
    # Strip markdown bold/italic formatting
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    # Strip markdown headers
    cleaned = re.sub(r"#{1,6}\s*", "", cleaned)
    # Strip backticks
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    # Clean whitespace
    return re.sub(r"\s+", " ", cleaned).strip()


class VoiceEngine:
    """Zero-cost neural TTS voice synthesizer using Microsoft Neural Voices."""

    def __init__(self, default_voice: str = DEFAULT_LADY_VOICE):
        self.default_voice = default_voice

    async def synthesize_to_bytes(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> bytes:
        """Synthesize text into MP3 audio bytes with cloned voice adaptation."""
        spoken_text = clean_text_for_speech(text)
        selected_voice = voice or self.default_voice
        applied_rate = rate
        applied_pitch = pitch

        # If text contains Devanagari Hindi characters, English voices cannot pronounce them!
        # Automatically route to Swara (Hindi) voice so it speaks fluid Hindi.
        has_devanagari = any("\u0900" <= char <= "\u097F" for char in spoken_text)
        if has_devanagari:
            selected_voice = DEFAULT_HINGLISH_VOICE

        # Check if custom cloned voice requested
        if selected_voice in ("custom_clone", "custom"):
            try:
                from packages.core.voice.cloner import voice_cloner
                profile = voice_cloner.get_current_profile()
                if profile:
                    selected_voice = profile.base_hindi_voice if has_devanagari else profile.base_english_voice
                    applied_pitch = profile.pitch_adjustment
                    applied_rate = profile.rate_adjustment
                else:
                    selected_voice = DEFAULT_HINGLISH_VOICE if has_devanagari else DEFAULT_LADY_VOICE
            except Exception:
                selected_voice = DEFAULT_HINGLISH_VOICE if has_devanagari else DEFAULT_LADY_VOICE
        elif has_devanagari:
            # If text contains Devanagari Hindi characters, ensure Hindi-capable neural model
            if not selected_voice.startswith("hi-"):
                selected_voice = DEFAULT_HINGLISH_VOICE

        communicate = edge_tts.Communicate(
            text=spoken_text,
            voice=selected_voice,
            rate=applied_rate,
            pitch=applied_pitch,
        )
        if not spoken_text.strip():
            return b""

        audio_stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])
        try:
            communicate = edge_tts.Communicate(
                text=spoken_text,
                voice=selected_voice,
                rate=applied_rate,
                pitch=applied_pitch,
            )

        return audio_stream.getvalue()
            audio_stream = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_stream.write(chunk["data"])

            return audio_stream.getvalue()
        except Exception:
            return b""

    async def synthesize_to_base64(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> str:
        """Synthesize text into a base64 MP3 data string ready for browser/client playback."""
        audio_bytes = await self.synthesize_to_bytes(text=text, voice=voice, rate=rate, pitch=pitch)
        return base64.b64encode(audio_bytes).decode("utf-8")
        try:
            audio_bytes = await self.synthesize_to_bytes(text=text, voice=voice, rate=rate, pitch=pitch)
            return base64.b64encode(audio_bytes).decode("utf-8") if audio_bytes else ""
        except Exception:
            return ""

