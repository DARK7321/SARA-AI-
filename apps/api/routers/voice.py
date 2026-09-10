"""Voice Studio & Cloning REST API router for OmniBrain."""
import base64
import os
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from apps.api.deps import get_db, get_current_user
from packages.core.db.models import User
from packages.core.schemas.common import APIResponse
from packages.core.voice.cloner import voice_cloner, VoiceProfile
from packages.core.voice.tts import VoiceEngine

router = APIRouter()


class VoiceUploadPayload(BaseModel):
    audio_base64: Optional[str] = Field(default=None, description="Base64 encoded audio string")
    filename: Optional[str] = Field(default="reference.wav", description="Audio filename")


class VoicePreviewPayload(BaseModel):
    text: str = Field(min_length=1, max_length=500, description="Sentence to synthesize with cloned voice")


@router.get("/clone/current", response_model=APIResponse)
async def get_current_voice_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Retrieve the currently active cloned voice profile and audio metadata."""
    trace_id = getattr(request.state, "trace_id", None)
    profile = voice_cloner.get_current_profile()
    active_voice = current_user.settings.get("active_voice", "auto") if current_user.settings else "auto"

    return APIResponse(
        ok=True,
        data={
            "has_profile": profile is not None,
            "profile": profile.model_dump() if profile else None,
            "active_voice": active_voice,
            "has_reference_audio": voice_cloner.audio_path.exists(),
        },
        trace_id=trace_id,
    )


@router.post("/clone/upload", response_model=APIResponse)
async def upload_voice_sample(
    request: Request,
    file: Optional[UploadFile] = File(None),
    payload: Optional[VoiceUploadPayload] = None,
    current_user: User = Depends(get_current_user),
):
    """Upload an audio sample (file or base64) to analyze and generate a cloned voice profile."""
    trace_id = getattr(request.state, "trace_id", None)
    raw_bytes = b""
    filename = "reference.wav"

    if file is not None:
        raw_bytes = await file.read()
        filename = file.filename or "reference.wav"
    elif payload and payload.audio_base64:
        try:
            # Handle potential data URL prefixes like data:audio/wav;base64,...
            b64_str = payload.audio_base64
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            raw_bytes = base64.b64decode(b64_str)
            filename = payload.filename or "reference.wav"
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid base64 audio: {e}")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No audio file or base64 data provided.")

    if len(raw_bytes) < 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio sample is too short. Please provide at least 1-2 seconds.")

    # Process and analyze sample
    try:
        profile = voice_cloner.process_and_save_sample(raw_bytes, filename=filename)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Voice analysis failed: {e}")

    return APIResponse(
        ok=True,
        data={"profile": profile.model_dump(), "message": "Voice sample analyzed and cloned successfully."},
        trace_id=trace_id,
    )


@router.post("/clone/preview", response_model=APIResponse)
async def preview_cloned_voice(
    payload: VoicePreviewPayload,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Synthesize a sample sentence using the cloned voice profile."""
    trace_id = getattr(request.state, "trace_id", None)
    profile = voice_cloner.get_current_profile()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cloned voice profile found. Please upload a voice sample first.",
        )

    voice_engine = VoiceEngine()
    try:
        audio_base64 = await voice_engine.synthesize_to_base64(
            text=payload.text,
            voice="custom_clone",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Voice synthesis failed: {e}")

    return APIResponse(
        ok=True,
        data={
            "audio_base64": audio_base64,
            "text": payload.text,
            "profile": profile.model_dump(),
        },
        trace_id=trace_id,
    )


@router.post("/clone/activate", response_model=APIResponse)
async def activate_cloned_voice(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set the cloned voice as the primary speaking voice for F.R.I.D.A.Y."""
    trace_id = getattr(request.state, "trace_id", None)
    profile = voice_cloner.get_current_profile()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cloned voice profile found. Please upload a voice sample first.",
        )

    user = await db.get(User, current_user.id)
    target_user = user if user is not None else current_user
    settings = dict(target_user.settings or {})
    settings["active_voice"] = "custom_clone"
    settings["custom_voice_profile_id"] = profile.profile_id
    target_user.settings = settings
    flag_modified(target_user, "settings")
    await db.commit()

    return APIResponse(
        ok=True,
        data={
            "active_voice": "custom_clone",
            "message": "Cloned voice activated! Friday will now speak with your custom voice.",
        },
        trace_id=trace_id,
    )


@router.get("/sample-audio")
async def get_reference_audio():
    """Stream the uploaded reference audio sample file."""
    if not voice_cloner.audio_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No reference audio found.")
    return FileResponse(
        path=str(voice_cloner.audio_path),
        media_type="audio/wav",
        filename="reference_voice.wav",
    )

