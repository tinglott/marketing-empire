"""Kokoro local TTS — free, offline, no API key.

Used as the local fallback voice when the online Edge service is
unreachable (and as a selectable engine in VoiceForge). The ``kokoro``
package runs the 82M-parameter Kokoro model on this computer's CPU and
downloads its voice model (~300 MB) from Hugging Face once, on first use.

If the package is not installed, every function here degrades cleanly:
``is_available()`` returns False and ``synthesize()`` raises RuntimeError,
so callers can fall through to their next option.
"""

from __future__ import annotations

import io
import threading

SAMPLE_RATE = 24000

# Curated American + British voices: (id, display name, gender).
KOKORO_VOICES = [
    {"id": "af_heart", "name": "Heart — Kokoro local (female)", "gender": "f"},
    {"id": "af_bella", "name": "Bella — Kokoro local (female)", "gender": "f"},
    {"id": "af_sarah", "name": "Sarah — Kokoro local (female)", "gender": "f"},
    {"id": "am_adam", "name": "Adam — Kokoro local (male)", "gender": "m"},
    {"id": "am_michael", "name": "Michael — Kokoro local (male)", "gender": "m"},
    {"id": "bf_emma", "name": "Emma — Kokoro local (British female)", "gender": "f"},
    {"id": "bm_george", "name": "George — Kokoro local (British male)", "gender": "m"},
]
KOKORO_VOICE_IDS = {v["id"] for v in KOKORO_VOICES}
KOKORO_FEMALE = "af_heart"
KOKORO_MALE = "am_adam"

_pipeline = None
_pipeline_lock = threading.Lock()
_package_checked: bool | None = None


def is_available() -> bool:
    """True when the ``kokoro`` package is installed (model may still need downloading)."""
    global _package_checked
    if _package_checked is None:
        try:
            import kokoro  # noqa: F401

            _package_checked = True
        except ImportError:
            _package_checked = False
    return _package_checked


def is_ready() -> bool:
    """True when Kokoro can synthesize immediately (package + model cached).

    Used by *automatic* fallback chains so a surprise ~300 MB download never
    starts mid-request. Explicit Kokoro mode may still trigger the one-time
    download via ``synthesize()``.
    """
    if not is_available():
        return False
    try:
        from huggingface_hub import try_to_load_from_cache

        return (
            try_to_load_from_cache("hexgrad/Kokoro-82M", "kokoro-v1_0.pth") is not None
        )
    except Exception:
        # If we can't check the cache, assume not ready rather than risk a
        # surprise download in an automatic fallback.
        return False


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                if not is_available():
                    raise RuntimeError(
                        "Kokoro is not installed (pip install kokoro). "
                        "Falling back to the next available voice."
                    )
                from kokoro import KPipeline

                _pipeline = KPipeline(
                    lang_code="a",  # American English
                    repo_id="hexgrad/Kokoro-82M",
                    device="cpu",
                )
    return _pipeline


def fallback_voice(gender: str | None) -> str:
    """Pick a Kokoro voice matching a gender hint ('f'/'m')."""
    return KOKORO_MALE if gender == "m" else KOKORO_FEMALE


def synthesize(text: str, voice: str = KOKORO_FEMALE, speed: float = 1.0) -> bytes:
    """Synthesize *text* with a Kokoro voice. Returns WAV bytes (24 kHz mono).

    The first call downloads the model (~300 MB, one time). Raises
    RuntimeError when Kokoro is unavailable.
    """
    if voice not in KOKORO_VOICE_IDS:
        voice = KOKORO_FEMALE
    pipeline = _get_pipeline()
    try:
        generator = pipeline(text, voice=voice, speed=speed)
    except TypeError:
        generator = pipeline(text, voice=voice)  # older kokoro: no speed kwarg
    import numpy as np
    import soundfile as sf

    chunks = []
    for _gs, _ps, audio in generator:
        chunks.append(audio.cpu().numpy() if hasattr(audio, "cpu") else audio)
    if not chunks:
        raise RuntimeError("Kokoro produced no audio")
    pcm = np.concatenate(chunks).astype("float32")
    buf = io.BytesIO()
    sf.write(buf, pcm, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return buf.getvalue()
