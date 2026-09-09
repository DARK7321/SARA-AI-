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
    # Replace F.R.I.D.A.Y. or variations with natural word 'Friday'
    cleaned = re.sub(r"(?i)f\.r\.i\.d\.a\.y\.?", "Friday", text)
    cleaned = re.sub(r"\bFRIDAY\b", "Friday", cleaned)
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
        """Synthesize text into MP3 audio bytes."""
        spoken_text = clean_text_for_speech(text)
        selected_voice = voice or self.default_voice

        # If text contains Devanagari Hindi characters, English voices cannot pronounce them!
        # Automatically route to Swara (Hindi) voice so it speaks fluid Hindi.
        has_devanagari = any("\u0900" <= char <= "\u097F" for char in spoken_text)
        if has_devanagari:
            selected_voice = DEFAULT_HINGLISH_VOICE

        communicate = edge_tts.Communicate(
            text=spoken_text,
            voice=selected_voice,
            rate=rate,
            pitch=pitch,
        )

        audio_stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])

        return audio_stream.getvalue()

    async def synthesize_to_base64(
        self,
        text: str,
        voice: Optional[str] = None,
    ) -> str:
        """Synthesize text into a base64 MP3 data string ready for browser/client playback."""
        audio_bytes = await self.synthesize_to_bytes(text=text, voice=voice)
        return base64.b64encode(audio_bytes).decode("utf-8")

