"""
GUNA-ASTRA Voice Engine
-----------------------
High-accuracy speech recognition using OpenAI Whisper (local, offline)
with Google Speech as fallback. Also handles TTS with multiple voice options.

WHY WHISPER?
  - Dramatically more accurate than SpeechRecognition + Google for noisy/accented input
  - Runs locally — no API key needed
  - Handles "play say yes to heaven on youtube" correctly

INSTALL:
  pip install openai-whisper sounddevice soundfile pyttsx3 faster-whisper
"""

import io
import logging
import os
import sys
import tempfile
import threading
import time

logger = logging.getLogger("GUNA-ASTRA.Voice")

# ─── Constants ────────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000  # Whisper native rate
CHANNELS = 1
SILENCE_LIMIT = 2.0  # seconds of silence = end of speech
MAX_RECORD = 30.0  # hard cap
ENERGY_THRESH = 0.008  # RMS threshold for voice activity detection


# ─── Whisper loader ───────────────────────────────────────────────────────────
_whisper_model = None
_whisper_lock = threading.Lock()


def _load_whisper(model_size: str = "base"):
    global _whisper_model
    with _whisper_lock:
        if _whisper_model is not None:
            return _whisper_model
        try:
            from faster_whisper import WhisperModel

            logger.info(f"Loading faster-whisper [{model_size}]...")
            _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
            logger.info("Whisper loaded ✓")
        except ImportError:
            try:
                import whisper

                logger.info(f"Loading openai-whisper [{model_size}]...")
                _whisper_model = whisper.load_model(model_size)
                logger.info("Whisper loaded ✓")
            except ImportError:
                logger.warning("Whisper not installed — using Google fallback")
                _whisper_model = "google"
    return _whisper_model


# ─── Recording ────────────────────────────────────────────────────────────────
def record_until_silence():
    """
    Records audio from microphone until silence is detected.
    Returns raw audio as float32 numpy array at 16kHz.
    """
    import queue as queue_module

    import numpy as np
    import sounddevice as sd

    q = queue_module.Queue()
    frames = []
    silent = 0.0
    started = False
    start_t = time.time()

    def callback(indata, frame_count, time_info, status):
        q.put(indata.copy())

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        callback=callback,
        blocksize=int(SAMPLE_RATE * 0.1),
    ):
        print("\n🎙️  Listening...", end="", flush=True)
        while True:
            chunk = q.get()
            rms = float(np.sqrt(np.mean(chunk**2)))

            if rms > ENERGY_THRESH:
                started = True
                silent = 0.0
                frames.append(chunk)
                print(".", end="", flush=True)
            else:
                if started:
                    silent += 0.1
                    frames.append(chunk)
                    if silent >= SILENCE_LIMIT:
                        break
                # not started yet — keep waiting
            if time.time() - start_t > MAX_RECORD:
                break

    print(" done", flush=True)
    if not frames:
        return np.array([], dtype="float32")
    return np.concatenate(frames, axis=0).flatten()


# ─── Transcription ────────────────────────────────────────────────────────────
def transcribe_audio(audio, model_size: str = "base") -> str:
    """
    Transcribes audio array to text.
    Tries faster-whisper → openai-whisper → Google fallback.
    """
    import numpy as np

    if len(audio) < SAMPLE_RATE * 0.3:  # less than 300ms → ignore
        return ""

    model = _load_whisper(model_size)

    # ── faster-whisper ──────────────────────────────
    try:
        from faster_whisper import WhisperModel

        if isinstance(model, WhisperModel):
            import soundfile as sf

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                sf.write(f.name, audio, SAMPLE_RATE)
                tmp = f.name
            segments, info = model.transcribe(
                tmp, beam_size=5, language="en", vad_filter=True
            )
            text = " ".join(s.text for s in segments).strip()
            os.unlink(tmp)
            return _clean_transcript(text)
    except Exception:
        pass

    # ── openai-whisper ──────────────────────────────
    try:
        import whisper

        if hasattr(model, "transcribe"):
            result = model.transcribe(audio, language="en", fp16=False, temperature=0)
            return _clean_transcript(result["text"])
    except Exception:
        pass

    # ── Google fallback ─────────────────────────────
    return _google_fallback(audio)


def _google_fallback(audio) -> str:
    try:
        import io
        import wave

        import numpy as np
        import speech_recognition as sr

        r = sr.Recognizer()
        audio_int16 = (audio * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())
        buf.seek(0)
        with sr.AudioFile(buf) as src:
            audio_data = r.record(src)
        return r.recognize_google(audio_data)
    except Exception as e:
        logger.warning(f"Google STT failed: {e}")
        return ""


def _clean_transcript(text: str) -> str:
    """Remove common Whisper hallucination artifacts."""
    hallucinations = [
        "thank you for watching",
        "thanks for watching",
        "please subscribe",
        "like and subscribe",
        "subtitles by",
        "[music]",
        "[applause]",
        "[laughing]",
    ]
    t = text.strip()
    for h in hallucinations:
        if t.lower() == h:
            return ""
    return t


# ─── Full voice input pipeline ────────────────────────────────────────────────
def listen(model_size: str = "base", timeout: float = 10.0) -> str:
    """
    High-level: record → transcribe → return text.
    Returns empty string on failure.
    """
    try:
        audio = record_until_silence()
        if len(audio) == 0:
            return ""
        text = transcribe_audio(audio, model_size)
        if text:
            logger.info(f"Voice → '{text}'")
        return text
    except Exception as e:
        logger.error(f"Voice listen error: {e}")
        return ""


# ─── TTS ──────────────────────────────────────────────────────────────────────
_tts_engine = None


def _get_tts():
    global _tts_engine
    if _tts_engine is None:
        import pyttsx3

        _tts_engine = pyttsx3.init()
        # Tune: rate 175 (natural), volume 0.95
        _tts_engine.setProperty("rate", 175)
        _tts_engine.setProperty("volume", 0.95)
        # Try to pick a good voice
        voices = _tts_engine.getProperty("voices")
        for v in voices:
            if "david" in v.id.lower() or "english" in v.id.lower():
                _tts_engine.setProperty("voice", v.id)
                break
    return _tts_engine


def speak(text: str, async_mode: bool = False):
    """Convert text to speech. async_mode=True returns immediately."""

    def _do_speak():
        try:
            engine = _get_tts()
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            logger.error(f"TTS error: {e}")
            print(f"🔊 {text}")  # fallback print

    if async_mode:
        t = threading.Thread(target=_do_speak, daemon=True)
        t.start()
    else:
        _do_speak()
