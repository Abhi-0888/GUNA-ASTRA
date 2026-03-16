"""
Wake Word Detection (openwakeword)
Listens continuously for "Hey Guna" with minimal CPU footprint.
"""

import queue
import time

import numpy as np

from utils.logger import get_logger

logger = get_logger("WakeWord")


class WakeWordDetector:
    def __init__(self, model_path="hey_guna"):
        # Note: openwakeword downloads pre-trained weights automatically
        # if using built-in words. For a custom "Hey Guna", we might
        # need to use a similar built-in like "hey jarvis" or train one.
        # For this implementation, we will use a flexible approach.
        self.model_path = model_path
        self.owwModel = None
        self.is_listening = False

    def initialize(self):
        try:
            import openwakeword
            from openwakeword.model import Model

            # Download models if they don't exist
            openwakeword.utils.download_models()

            # Using multiple high-quality pre-trained models as triggers
            # 'hey jarvis' and 'alexa' are very robust in openwakeword
            self.owwModel = Model(
                wakeword_models=["hey_jarvis_v0.1", "alexa_v0.1", "hey_mycroft_v0.1"],
                inference_framework="onnx",
            )
            logger.info(
                "Wake word models (Jarvis/Alexa/Mycroft) initialized as triggers."
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize openwakeword: {e}")
            return False

    def listen_for_wake_word(self, audio_queue: queue.Queue) -> bool:
        """
        Consumes audio chunks from the queue and checks for the wake word.
        Blocks until wake word is detected or is_listening becomes False.
        """
        if not self.owwModel:
            if not self.initialize():
                time.sleep(1)
                return False

        self.is_listening = True
        logger.info("Listening for wake word...")

        try:
            while self.is_listening:
                try:
                    # Get 1280 samples (16kHz, mono, int16)
                    chunk = audio_queue.get(timeout=0.5)

                    # Convert to numpy array expected by openwakeword
                    audio_data = np.frombuffer(chunk, dtype=np.int16)

                    # Feed to model
                    prediction = self.owwModel.predict(audio_data)

                    # Check scores
                    for mdl_name, score in prediction.items():
                        if (
                            score > 0.4
                        ):  # Slightly lower threshold for better sensitivity
                            logger.info(
                                f"Wake word detected! ({mdl_name} score: {score:.2f})"
                            )
                            self.is_listening = False
                            return True

                except queue.Empty:
                    continue
        except Exception as e:
            logger.error(f"Error during wake word detection: {e}")

        self.is_listening = False
        return False

    def stop(self):
        self.is_listening = False
