"""
app.py — VoiceShift AI: Male-to-Female Voice Conversion
=========================================================
Full-stack FastAPI backend serving the HTML frontend and
processing voice conversion via ElevenLabs Speech-to-Speech API.

Requirements:
    pip install -r requirements.txt

Run:
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload

Environment:
    export ELEVENLABS_API_KEY="your_elevenlabs_api_key_here"
"""

import os
import uuid
import logging
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, AsyncIterator

import aiofiles
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# ElevenLabs SDK import (fail loudly with a clear message)
# ---------------------------------------------------------------------------
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings
except ImportError as exc:
    raise SystemExit(
        "[FATAL] elevenlabs SDK not installed or incompatible.\n"
        "Fix: pip install -r requirements.txt\n"
        f"Original error: {exc}"
    ) from exc

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("voiceshift")

# ---------------------------------------------------------------------------
# API key validation — fail at startup, not at first request
# ---------------------------------------------------------------------------
ELEVENLABS_API_KEY: str = os.environ.get("ELEVENLABS_API_KEY", "").strip()
if not ELEVENLABS_API_KEY:
    raise SystemExit(
        "\n"
        "FATAL: ELEVENLABS_API_KEY environment variable is not set.\n"
        "Export it before starting the server:\n"
        "    export ELEVENLABS_API_KEY='sk-...'\n"
    )

# ---------------------------------------------------------------------------
# ElevenLabs client — initialised once at module level (thread-safe singleton)
# ---------------------------------------------------------------------------
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
logger.info("ElevenLabs client initialised successfully.")

# ---------------------------------------------------------------------------
# Voice catalogue — high-quality female voices available in the UI
# ---------------------------------------------------------------------------
FEMALE_VOICES: dict[str, str] = {
    "21m00Tcm4TlvDq8ikWAM": "Rachel - Warm & Natural",
    "ThT5KcBeYPX3keUQqHPh": "Dorothy - Soft & Gentle",
    "EXAVITQu4vr4xnSDxMaL": "Bella - Smooth & Professional",
    "MF3mGyEYCl7XYWbV9V6O": "Elli - Young & Expressive",
    "jBpfuIE2acCO8z3wKNLl": "Gigi - Bright & Energetic",
    "oWAxZDx7w5VEj9dCyTzz": "Grace - Calm & Clear",
}

# ---------------------------------------------------------------------------
# Temporary file directories — created on startup, cleaned per-request
# ---------------------------------------------------------------------------
TMP_DIR = Path(tempfile.gettempdir()) / "voiceshift"
TMP_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Temporary file directory: {TMP_DIR}")

# ---------------------------------------------------------------------------
# Frontend path resolution
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
FRONTEND_HTML = BASE_DIR / "index.html"


# ---------------------------------------------------------------------------
# Lifespan context manager (replaces deprecated @app.on_event hooks)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("=" * 60)
    logger.info("  VoiceShift AI server starting up")
    logger.info(f"  ElevenLabs API key: {'*' * 8}{ELEVENLABS_API_KEY[-4:]}")
    logger.info(f"  Available voices:   {len(FEMALE_VOICES)}")
    logger.info(f"  Temp directory:     {TMP_DIR}")
    logger.info("=" * 60)
    try:
        yield
    finally:
        for f in TMP_DIR.iterdir():
            try:
                f.unlink()
            except OSError:
                pass
        logger.info("Temporary files purged. Server shut down cleanly.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="VoiceShift AI",
    description="Male-to-female voice conversion powered by ElevenLabs Speech-to-Speech.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# CORS — allow all origins in development (lock this down in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# GET / — Serve the frontend
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_frontend() -> HTMLResponse:
    """Serve the single-page frontend application."""
    if not FRONTEND_HTML.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Frontend file not found at '{FRONTEND_HTML}'. "
                "Make sure index.html is in the same directory as app.py."
            ),
        )
    html_content = FRONTEND_HTML.read_text(encoding="utf-8")
    return HTMLResponse(content=html_content, status_code=200)


# ---------------------------------------------------------------------------
# GET /api/voices — return available voice catalogue to the frontend
# ---------------------------------------------------------------------------
@app.get("/api/voices")
async def get_voices() -> dict:
    """Return the available female voice options as JSON."""
    return {
        "voices": [
            {"id": vid, "name": vname}
            for vid, vname in FEMALE_VOICES.items()
        ]
    }


# ---------------------------------------------------------------------------
# Background cleanup helper
# ---------------------------------------------------------------------------
def _cleanup_file(path: Path) -> None:
    """Best-effort deletion of a temp file once the response is sent."""
    try:
        if path.exists():
            path.unlink()
    except OSError as e:
        logger.warning(f"Could not delete temp file '{path}': {e}")


# ---------------------------------------------------------------------------
# POST /api/convert-voice — core conversion endpoint
# ---------------------------------------------------------------------------
@app.post("/api/convert-voice")
async def convert_voice(
    background_tasks: BackgroundTasks,
    audio: Annotated[UploadFile, File(description="Source audio blob (wav/mp3/ogg/m4a).")],
    voice_id: Annotated[str, Form(description="ElevenLabs target female Voice ID.")] = "21m00Tcm4TlvDq8ikWAM",
    stability: Annotated[float, Form(description="Voice stability 0.0-1.0.")] = 0.40,
    similarity_boost: Annotated[float, Form(description="Similarity boost 0.0-1.0.")] = 0.85,
    style: Annotated[float, Form(description="Style exaggeration 0.0-1.0.")] = 0.35,
) -> FileResponse:
    """
    Accept an uploaded audio file and optional voice parameters,
    send to ElevenLabs Speech-to-Speech API, and return the
    converted female-voice MP3 as a FileResponse.
    """
    # Parameter validation
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file received.")

    if voice_id not in FEMALE_VOICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown voice_id '{voice_id}'. Valid IDs: {list(FEMALE_VOICES.keys())}",
        )

    for name, val, lo, hi in [
        ("stability", stability, 0.0, 1.0),
        ("similarity_boost", similarity_boost, 0.0, 1.0),
        ("style", style, 0.0, 1.0),
    ]:
        if not (lo <= val <= hi):
            raise HTTPException(
                status_code=422,
                detail=f"Parameter '{name}' must be between {lo} and {hi}, got {val}.",
            )

    # Unique request identifier (prevents filename collisions)
    request_id = uuid.uuid4().hex
    suffix = Path(audio.filename).suffix.lower() or ".wav"
    input_path = TMP_DIR / f"input_{request_id}{suffix}"
    output_path = TMP_DIR / f"output_{request_id}.mp3"

    logger.info(
        f"[{request_id[:8]}] Received: '{audio.filename}' | "
        f"Voice: {FEMALE_VOICES.get(voice_id, voice_id)} | "
        f"stability={stability} similarity={similarity_boost} style={style}"
    )

    try:
        # 1. Save the incoming upload to a temp file
        async with aiofiles.open(input_path, "wb") as tmp_file:
            while True:
                chunk = await audio.read(524288)  # 512 KB
                if not chunk:
                    break
                await tmp_file.write(chunk)

        input_size_kb = input_path.stat().st_size / 1024
        logger.info(f"[{request_id[:8]}] Saved input: {input_size_kb:.1f} KB -> {input_path.name}")

        # 2. Build ElevenLabs VoiceSettings (serialised to JSON for the SDK)
        voice_settings = VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            use_speaker_boost=True,
        )

        # 3. Call ElevenLabs Speech-to-Speech API
        logger.info(f"[{request_id[:8]}] Sending to ElevenLabs S2S API...")

        with open(input_path, "rb") as audio_file:
            audio_stream = elevenlabs_client.speech_to_speech.convert(
                voice_id=voice_id,
                audio=audio_file,
                voice_settings=voice_settings.json(),
                model_id="eleven_english_sts_v2",
                output_format="mp3_44100_128",
            )

            # 4. Stream response chunks to output file (inside `with` so the
            #    input file stays open until the SDK finishes reading it)
            total_bytes = 0
            with open(output_path, "wb") as out_file:
                for chunk in audio_stream:
                    if chunk:
                        out_file.write(chunk)
                        total_bytes += len(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=502,
                detail="ElevenLabs returned an empty audio stream. Check your API key and quota.",
            )

        output_size_kb = total_bytes / 1024
        logger.info(
            f"[{request_id[:8]}] Conversion complete: "
            f"{input_size_kb:.1f} KB input -> {output_size_kb:.1f} KB output"
        )

        # 5. Schedule cleanup of both temp files after the response is sent
        background_tasks.add_task(_cleanup_file, input_path)
        background_tasks.add_task(_cleanup_file, output_path)

        # 6. Return the MP3 file to the client
        return FileResponse(
            path=str(output_path),
            media_type="audio/mpeg",
            filename="voiceshift_female_output.mp3",
            background=background_tasks,
        )

    except HTTPException:
        _cleanup_file(input_path)
        _cleanup_file(output_path)
        raise

    except Exception as exc:
        logger.error(f"[{request_id[:8]}] Conversion failed: {exc}", exc_info=True)
        _cleanup_file(input_path)
        _cleanup_file(output_path)
        raise HTTPException(
            status_code=500,
            detail=(
                f"Voice conversion failed: {str(exc)}. "
                "Check server logs for details."
            ),
        ) from exc


# ---------------------------------------------------------------------------
# Health check endpoint — useful for container orchestration probes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check() -> dict:
    return {
        "status": "healthy",
        "service": "VoiceShift AI",
        "elevenlabs_key_set": bool(ELEVENLABS_API_KEY),
        "voices_available": len(FEMALE_VOICES),
        "tmp_dir": str(TMP_DIR),
    }
