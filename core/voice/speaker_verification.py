"""
Speaker Verification (Resemblyzer)
Extracts voice embeddings and compares them against the authorized user's template.
"""

import os

import numpy as np

from utils.logger import get_logger

logger = get_logger("SpeakerVerification")


class SpeakerVerifier:
    def __init__(self, embedding_path: str, threshold: float = 0.75):
        self.embedding_path = embedding_path
        self.threshold = threshold
        self.encoder = None
        self.authorized_embedding = None

    def initialize(self):
        """Load the Resemblyzer model and the authorized user's profile."""
        try:
            from resemblyzer import VoiceEncoder

            # This loads the pre-trained Voice Encoder weights
            self.encoder = VoiceEncoder()
            logger.info("Resemblyzer VoiceEncoder loaded.")

            # Load authorized user profile if it exists
            if os.path.exists(self.embedding_path):
                self.authorized_embedding = np.load(self.embedding_path)
                logger.info(
                    f"Loaded authorized voice embedding from {self.embedding_path}"
                )
            else:
                logger.warning(
                    f"No authorized voice embedding found at {self.embedding_path}!"
                )
                logger.warning(
                    "Please run `scripts/enroll_voice.py` to secure the system."
                )

            return True
        except ImportError:
            logger.error("Failed to import Resemblyzer. Please ensure it is installed.")
            return False
        except Exception as e:
            logger.error(f"Error initializing SpeakerVerifier: {e}")
            return False

    def verify_audio(self, wav_path: str) -> dict:
        """
        Verify if the audio at wav_path belongs to the authorized user.
        Returns a dict with success boolean and similarity score.
        """
        if self.encoder is None:
            if not self.initialize():
                return {"success": False, "score": 0.0, "error": "Model not loaded"}

        if self.authorized_embedding is None:
            # If no enrolled voice exists, we might reject everything (strict mode)
            # or allow everything (setup mode). For security, reject.
            return {
                "success": False,
                "score": 0.0,
                "error": "No authorized voice enrolled. Run enroll_voice.py.",
            }

        try:
            from resemblyzer import preprocess_wav

            # Load and preprocess the newly recorded command
            wav = preprocess_wav(wav_path)

            # Generate embedding for the new command
            new_embedding = self.encoder.embed_utterance(wav)

            # Compare with authorized embedding using cosine similarity
            similarity = np.dot(self.authorized_embedding, new_embedding) / (
                np.linalg.norm(self.authorized_embedding)
                * np.linalg.norm(new_embedding)
            )

            is_authorized = bool(similarity >= self.threshold)

            logger.info(
                f"Voice similarity score: {similarity:.3f} (Threshold: {self.threshold})"
            )
            if is_authorized:
                logger.info("✅ Voice verified: Authorized User.")
            else:
                logger.warning("❌ Voice rejected: Unauthorized User.")

            return {"success": is_authorized, "score": float(similarity)}

        except Exception as e:
            logger.error(f"Error during voice verification: {e}")
            return {"success": False, "score": 0.0, "error": str(e)}

    def generate_and_save_embedding(
        self, wav_paths: list, save_path: str = None
    ) -> bool:
        """
        Generates an embedding from multiple clear audio samples of the user.
        Used by the enrollment script.
        """
        if self.encoder is None:
            if not self.initialize():
                return False

        save_path = save_path or self.embedding_path

        try:
            from resemblyzer import preprocess_wav

            embeddings = []
            for path in wav_paths:
                wav = preprocess_wav(path)
                emb = self.encoder.embed_utterance(wav)
                embeddings.append(emb)

            # Average the embeddings for a more robust template
            if embeddings:
                master_embedding = np.mean(embeddings, axis=0)
                # Normalize
                master_embedding = master_embedding / np.linalg.norm(master_embedding)

                # Ensure directory exists
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                np.save(save_path, master_embedding)

                self.authorized_embedding = master_embedding
                logger.info(
                    f"✅ Successfully saved master voice profile to {save_path}"
                )
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return False
