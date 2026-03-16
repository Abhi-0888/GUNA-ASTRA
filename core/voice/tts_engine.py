"""
Text-to-Speech Engine
Converts GUNA-ASTRA's responses into spoken audio using a Hindi female voice.
Utilizes Windows native SAPI5 for lightweight, offline text synthesis.
"""

import pyttsx3

from utils.logger import get_logger

logger = get_logger("TTSEngine")


class TTSEngine:
    def __init__(self, rate=150):
        self.engine = None
        self.rate = rate
        self.voice_id = None

    def initialize(self):
        try:
            self.engine = pyttsx3.init("sapi5")
            self.engine.setProperty("rate", self.rate)

            # Try to find a female Hindi or natural English voice
            voices = self.engine.getProperty("voices")
            selected_voice = None

            for voice in voices:
                name_low = voice.name.lower()
                # Prioritize a Windows native Hindi/India female voice if installed
                # Example: "Microsoft Kalpana" or "Microsoft Heera"
                if "hindi" in name_low or "india" in name_low:
                    if (
                        "zira" in name_low
                        or "kalpana" in name_low
                        or "female" in name_low
                    ):
                        selected_voice = voice.id
                        break
                elif "zira" in name_low or "female" in name_low:
                    # Fallback to standard female English voice if no Hindi specific found
                    selected_voice = voice.id

            if selected_voice:
                self.engine.setProperty("voice", selected_voice)
                self.voice_id = selected_voice
                logger.info("TTS initialized with a female/local voice.")
            else:
                logger.warning(
                    "Could not find optimal female Hindi voice, using default."
                )

            return True
        except Exception as e:
            logger.error(f"Failed to initialize TTS Engine: {e}")
            self.engine = None
            return False

    def speak(self, text: str):
        """
        Synthesizes text. This is a blocking call unless stop() is called from another thread.
        """
        if not text:
            return

        if not self.engine:
            if not self.initialize():
                return

        try:
            logger.info(f"Speaking: {text}")
            self.engine.say(text)
            self.engine.runAndWait()
        except RuntimeError:
            # This happens if stop() is called mid-speech; we ignore it.
            pass
        except Exception as e:
            logger.error(f"TTS Engine error: {e}")

    def stop(self):
        """Interrupts current speech."""
        if self.engine:
            try:
                self.engine.stop()
                logger.info("TTS speech interrupted.")
            except Exception as e:
                logger.error(f"Failed to stop TTS: {e}")
