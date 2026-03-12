"""
Speech-to-Text Engine (faster-whisper)
Converts authorized user's spoken audio into text commands.
Fast, local, and supports multiple languages (English/Hindi).

v2: Includes smart voice correction for common mishears.
"""

import os
import re

from utils.logger import get_logger

logger = get_logger("STTEngine")

# v2: Common speech-to-text corrections
VOICE_CORRECTIONS = {
    "you tube": "youtube",
    "you too": "youtube",
    "u tube": "youtube",
    "plate": "play",
    "clay": "play",
    "grey": "play",
    "pray": "play",
    "hoping": "open",
    "vs code": "vscode",
    "be as code": "vscode",
    "this cord": "discord",
    "say yes the heaven": "say yes to heaven",
    "staying heaven": "say yes to heaven",
    "sea yes to heaven": "say yes to heaven",
    "bohemian rap city": "bohemian rhapsody",
    "bohemian rap soda": "bohemian rhapsody",
    "star boy": "starboy",
    "blind in life": "blinding lights",
    "shape of u": "shape of you",
    "what is my name": "what's my name",
}

HALLUCINATIONS = [
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "like and subscribe",
    "subtitles by",
    "[music]",
    "[applause]",
]


class STTEngine:
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = None

    def initialize(self):
        try:
            from faster_whisper import WhisperModel

            logger.info(f"Loading Whisper model ({self.model_size})...")
            self.model = WhisperModel(
                self.model_size, device="cpu", compute_type="int8"
            )
            logger.info("Whisper STT initialized successfully.")
            return True
        except ImportError:
            logger.error("Failed to import faster_whisper. Is it installed?")
            return False
        except Exception as e:
            logger.error(f"Error initializing STT Engine: {e}")
            return False

    def transcribe(self, audio_path: str) -> str:
        """Transcribes an audio file into text with v2 smart corrections."""
        if not self.model:
            if not self.initialize():
                return ""

        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found for STT: {audio_path}")
            return ""

        try:
            logger.info("Transcribing audio...")
            segments, info = self.model.transcribe(audio_path, beam_size=5)

            logger.debug(
                f"Detected language '{info.language}' with probability {info.language_probability:.2f}"
            )

            text = " ".join([segment.text for segment in segments]).strip()

            # v2: Apply smart corrections
            text = self._apply_corrections(text)

            logger.info(f"Transcribed Text: '{text}'")
            return text

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""

    def _apply_corrections(self, text: str) -> str:
        """v2: Fix common Whisper mishears and hallucinations."""
        # Remove hallucinations
        t = text.strip()
        if t.lower() in HALLUCINATIONS:
            return ""

        # Apply word-level corrections
        result = t.lower()
        for wrong, right in VOICE_CORRECTIONS.items():
            if wrong in result:
                result = result.replace(wrong, right)

        # Clean up spacing
        result = re.sub(r"\s+", " ", result).strip()
        return result if result != t.lower() else t
