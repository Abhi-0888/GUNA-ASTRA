"""
Speech-to-Text Engine (faster-whisper)
Converts authorized user's spoken audio into text commands.
Fast, local, and supports multiple languages (English/Hindi).
"""

import os
from utils.logger import get_logger

logger = get_logger("STTEngine")


class STTEngine:
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = None

    def initialize(self):
        try:
            from faster_whisper import WhisperModel
            
            # Load the model. 'base' model is a good mix of speed and accuracy.
            # compute_type="int8" reduces memory usage for CPU/lower end GPUs
            logger.info(f"Loading Whisper model ({self.model_size})...")
            self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            logger.info("Whisper STT initialized successfully.")
            return True
        except ImportError:
            logger.error("Failed to import faster_whisper. Is it installed?")
            return False
        except Exception as e:
            logger.error(f"Error initializing STT Engine: {e}")
            return False

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribes an audio file into text.
        Returns the recognized text string.
        """
        if not self.model:
            if not self.initialize():
                return ""

        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found for STT: {audio_path}")
            return ""

        try:
            logger.info("Transcribing audio...")
            # We don't force a language so it auto-detects English vs Hindi
            # Return full text from all segments
            segments, info = self.model.transcribe(audio_path, beam_size=5)
            
            logger.debug(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")
            
            text = " ".join([segment.text for segment in segments]).strip()
            logger.info(f"Transcribed Text: '{text}'")
            return text
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""
