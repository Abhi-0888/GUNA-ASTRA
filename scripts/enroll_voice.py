"""
GUNA-ASTRA Secure Voice Enrollment Module

This script must be run by the authorized user to generate their unique Voice Print.
The print is saved securely and verified against all future voice commands.
"""

import os
import sys
import time

import numpy as np
import scipy.io.wavfile as wavfile
import sounddevice as sd
from resemblyzer import VoiceEncoder, preprocess_wav

# Paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
EMBEDDING_PATH = os.path.join(DATA_DIR, "user_embedding.npy")
TEMP_WAV = os.path.join(DATA_DIR, ".temp_enroll.wav")


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)


def record_audio(duration: int, prompt: str) -> str:
    print(f"\n{prompt}")
    print("Recording starts in...")
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)

    print("\n[ RECORDING ] Speak now...")

    # 16kHz mono is required by Resemblyzer
    fs = 16000
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="int16")
    sd.wait()
    print("[ STOPPED ]")

    wavfile.write(TEMP_WAV, fs, recording)
    return TEMP_WAV


def main():
    print("=" * 60)
    print("   GUNA-ASTRA — SECURE VOICE ENROLLMENT".center(60))
    print("=" * 60)
    print("\nTo secure your local AI assistant, we must generate a unique")
    print("voice fingerprint (embedding) so GUNA-ASTRA only obeys YOU.")
    print("\nWe will record 3 short phrases.")
    print("Please sit in a quiet room and speak clearly.")

    input("\nPress ENTER when you are ready to begin...")

    ensure_dirs()
    print("\nLoading AI Voice Encoder Model... (This takes a moment)")
    try:
        encoder = VoiceEncoder()
    except Exception as e:
        print(f"\n❌ Failed to load VoiceEncoder. Are dependencies installed? {e}")
        return

    embeddings = []

    # Phrase 1
    wav_path = record_audio(
        duration=6,
        prompt='PHRASE 1/3: Please read the following sentence naturally:\n"Hey Guna, establish a secure connection and prepare for my commands."',
    )
    embeddings.append(encoder.embed_utterance(preprocess_wav(wav_path)))

    # Phrase 2
    wav_path = record_audio(
        duration=6,
        prompt='PHRASE 2/3: Please read the following sentence naturally:\n"I am the authorized user of this system, verify my voice pattern now."',
    )
    embeddings.append(encoder.embed_utterance(preprocess_wav(wav_path)))

    # Phrase 3
    wav_path = record_audio(
        duration=5,
        prompt='PHRASE 3/3: Just say your wake word a few times with short pauses:\n"Hey Guna... Hey Guna... Hey Guna."',
    )
    embeddings.append(encoder.embed_utterance(preprocess_wav(wav_path)))

    # Cleanup temp audio
    if os.path.exists(TEMP_WAV):
        os.remove(TEMP_WAV)

    print("\n" + "=" * 60)
    print("Processing vocal characteristics and generating embedding...")

    # Average the three embeddings for a more robust profile
    master_embedding = np.mean(embeddings, axis=0)
    # Normalize to length 1
    master_embedding = master_embedding / np.linalg.norm(master_embedding)

    try:
        np.save(EMBEDDING_PATH, master_embedding)
        print(f"\n✅ SUCCESS! Voice Print securely saved to:\n   {EMBEDDING_PATH}")
        print("\nGUNA-ASTRA will now strictly obey commands possessing a > 75% match")
        print("against this vocal signature.")
        print("\nYou may now start GUNA-ASTRA with voice capabilities:")
        print("    python main.py --voice")
    except Exception as e:
        print(f"\n❌ Error saving voice embedding: {e}")


if __name__ == "__main__":
    main()
