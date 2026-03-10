import os
import queue
import time
import threading
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wavfile
from datetime import datetime

from config.settings import (
    VOICE_MODE_ENABLED,
    USER_VOICE_EMBEDDING_PATH,
    SPEAKER_VERIFICATION_THRESHOLD,
    STT_MODEL_SIZE,
    TTS_ENGINE,
    TTS_VOICE_RATE,
    MODE_NORMAL,
    MODE_WORKING
)
from utils.logger import get_logger

logger = get_logger("VoiceManager")


class VoiceManager:
    """
    Orchestrates the continuous listening, wake word detection, speaker
    authentication, and text translation pipeline.
    """
    def __init__(self, orchestrator):
        # We hold a reference to the main orchestrator so we can inject commands
        self.orchestrator = orchestrator
        self.is_running = False
        
        # We need a continuous audio stream buffer for openwakeword
        self.audio_queue = queue.Queue(maxsize=100)
        self.mic_stream = None
        
        # Audio formatting constants suitable for openwakeword & resemblyzer
        self.SAMPLE_RATE = 16000
        self.CHUNK_SIZE = 1280

        # Sub-modules
        self.wake_detector = None
        self.speaker_verifier = None
        self.stt_engine = None
        self.tts_engine = None
        
        # Interruption logic
        self.interrupted = threading.Event()
        self.is_busy = False # True while processing/speaking

    def initialize_modules(self):
        """Lazy-loads the heavy ML modules only when Voice Mode is activated."""
        try:
            # 1. Initialize TTS first to provide feedback during long downloads
            from core.voice.tts_engine import TTSEngine
            self.tts_engine = TTSEngine(rate=TTS_VOICE_RATE)
            if not self.tts_engine.initialize():
                logger.error("Failed to initialize TTS engine early.")
            else:
                self.tts_engine.speak("GUNA-ASTRA is initializing speech models. This may take a moment on the first run.")

            logger.info("Initializing Voice ML Models... this may take a moment.")
            
            from core.voice.wake_word import WakeWordDetector
            from core.voice.speaker_verification import SpeakerVerifier
            from core.voice.stt_engine import STTEngine
            
            self.wake_detector = WakeWordDetector()
            self.speaker_verifier = SpeakerVerifier(
                embedding_path=USER_VOICE_EMBEDDING_PATH,
                threshold=SPEAKER_VERIFICATION_THRESHOLD
            )
            self.stt_engine = STTEngine(model_size=STT_MODEL_SIZE)
            
            # Start heavy loading
            res_wake = self.wake_detector.initialize()
            res_speak = self.speaker_verifier.initialize()
            res_stt = self.stt_engine.initialize()
            
            if all([res_wake, res_speak, res_stt]):
                logger.info("✅ All Voice Modules Initialized successfully.")
                return True
            else:
                logger.error("❌ Failed to initialize one or more voice modules.")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing voice modules: {e}")
            return False

    def audio_callback(self, indata, frames, time, status):
        """Callback for the sounddevice input stream."""
        if status:
            logger.debug(f"Audio stream status: {status}")
        if self.is_running:
            try:
                # Put exact copy of the raw buffer into queue for Wakeword
                # and maintain a rolling buffer for when recording commands
                self.audio_queue.put_nowait(indata.copy())
            except queue.Full:
                pass

    def record_command(self, max_seconds=10, silence_seconds=0.8, output_wav="temp_command.wav") -> str:
        """
        Record audio from microphone until silence is detected or max_seconds is reached.
        Uses a simple energy-based VAD to stop recording immediately after speaking.
        """
        logger.info("🎙️ Recording command (speak now)...")
        
        recorded_frames = []
        # Calculate samples for silence threshold
        silence_chunks = int((self.SAMPLE_RATE / self.CHUNK_SIZE) * silence_seconds)
        max_chunks = int((self.SAMPLE_RATE / self.CHUNK_SIZE) * max_seconds)
        
        # Energy threshold for silence (matching what we used in the resemblyzer patch)
        energy_threshold = 0.02 

        # Flush the queue
        while not self.audio_queue.empty():
            try: self.audio_queue.get_nowait()
            except queue.Empty: break
                
        silent_count = 0
        has_started_speaking = False
        
        for i in range(max_chunks):
            if not self.is_running:
                break
            try:
                chunk = self.audio_queue.get(timeout=2.0)
                recorded_frames.append(chunk)
                
                # Check for voice activity
                audio_data = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                energy = np.sqrt(np.mean(audio_data**2))
                
                if energy > energy_threshold:
                    silent_count = 0
                    has_started_speaking = True
                else:
                    if has_started_speaking:
                        silent_count += 1
                
                # Stop if silence threshold met after speaking started
                if has_started_speaking and silent_count > silence_chunks:
                    logger.info("Silence detected. Stopping recording.")
                    break
                    
            except queue.Empty:
                break
                
        if not recorded_frames:
            return None
            
        audio_data = np.concatenate(recorded_frames, axis=0)
        os.makedirs("tmp", exist_ok=True)
        out_path = os.path.join("tmp", output_wav)
        wavfile.write(out_path, self.SAMPLE_RATE, audio_data)
        return out_path

    def flush_audio(self):
        """Clears anything currently in the audio queue to prevent echo triggers."""
        # logger.debug("Flushing audio queue...")
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

    def start_listening(self):
        """Starts the infinite voice processing loop with interruption support."""
        if not self.initialize_modules():
            logger.error("Voice Manager cannot start due to failing initialization.")
            return

        self.is_running = True
        
        logger.info("Starting microphone stream...")
        try:
            self.mic_stream = sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                blocksize=self.CHUNK_SIZE,
                device=None,
                channels=1,
                dtype="int16",
                callback=self.audio_callback
            )
            self.mic_stream.start()
        except Exception as e:
            logger.error(f"Failed to access microphone: {e}")
            self.is_running = False
            return

        self.tts_engine.speak("Voice systems online. Listening for wake word.")

        # Main Loop
        try:
            while self.is_running:
                # 1. Listen for "Hey Guna" (this blocks until detected)
                print("\r[LISTENING...] Say 'Hey Guna' ", end="", flush=True)
                self.interrupted.clear()
                detected = self.wake_detector.listen_for_wake_word(self.audio_queue)
                
                if detected and self.is_running:
                    print("\n🔔 WAKE WORD DETECTED")
                    self.is_busy = True
                    self.tts_engine.speak("Yes?")
                    self.flush_audio() # Don't listen to echos of "Yes?"
                    
                    # 2. Record command
                    temp_wav = self.record_command(max_seconds=8)
                    
                    if temp_wav:
                        # 3. Speaker Verification
                        verif_result = self.speaker_verifier.verify_audio(temp_wav)
                        
                        if verif_result.get("success"):
                            # 4. Speech-to-Text
                            user_text = self.stt_engine.transcribe(temp_wav)
                            
                            if user_text:
                                # JUNK FILTER: Strip symbols and check length
                                import re
                                filtered_text = re.sub(r'[^\w\s]', '', user_text).strip()
                                
                                if len(filtered_text) < 3:
                                    # Too short or just symbols
                                    print(f"[VOICE] ⚠️ Ignored junk/short transcription: '{user_text}'")
                                    self.tts_engine.speak("Tell me again, I missed that.")
                                    self.is_busy = False
                                    continue
                                
                                print(f"[USER SAYS] 🗣️  \"{user_text}\"")
                                
                                # Check for "Stop" intent immediately
                                if user_text.lower() in ["stop", "quiet", "shut up", "halt", "cancel"]:
                                    self.tts_engine.stop()
                                    self.is_busy = False
                                    continue

                                # 5. Pass to Orchestrator
                                if self.orchestrator.current_mode != MODE_NORMAL:
                                    self.tts_engine.speak("Checking on that.")
                                    
                                # Run orchestration and monitor for interruption
                                self._run_interruptible_task(user_text)
                                
                            else:
                                logger.warning("Empty transcription.")
                                self.tts_engine.speak("Tell me again, I missed that.")
                        else:
                            print(f"[AUTH] ❌ Verification Failed")
                            self.tts_engine.speak("Unauthorized voice detected.")
                    
                    # Clean up
                    if temp_wav and os.path.exists(temp_wav):
                        try: os.remove(temp_wav)
                        except: pass
                    
                    self.is_busy = False
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Voice Manager interrupted.")
        finally:
            self.stop()

    def _run_interruptible_task(self, user_text):
        """Runs the orchestrator command and allows the wake word to interrupt it."""
        # Start a thread to listen for interruption during processing/speaking
        interrupter_thread = threading.Thread(target=self._interruption_monitor, daemon=True)
        interrupter_thread.start()
        
        try:
            response = self.orchestrator.process_voice_command(user_text)
            if response and not self.interrupted.is_set():
                import re
                clean_text = re.sub(r'[*_#`]', '', str(response))
                clean_text = clean_text.encode('ascii', 'ignore').decode('ascii')
                
                # Take first 2 sentences for natural reply
                sentences = clean_text.split(". ")
                short_resp = ". ".join(sentences[:2])
                
                print(f"[GUNA-ASTRA SPEAKS] 🔊 \"{short_resp}\"")
                
                # The tts_engine.speak will block here, but the monitor thread can call stop()
                self.tts_engine.speak(short_resp)
                self.flush_audio() # Prevent echo of response from triggering next wake
        except Exception as e:
            logger.error(f"Error in task execution: {e}")
        finally:
            self.interrupted.set() # Signal monitor to stop

    def _interruption_monitor(self):
        """Background listener that halts speech/tasks if 'Hey Guna' or 'Stop' is heard."""
        monitor_detector = self.wake_detector # Re-use or use a fresh copy? 
        # Note: openwakeword Model objects are generally not thread-safe if shared, 
        # but here we are alternating between main loop listen and this monitor.
        
        # We need a new model instance for the background thread if we want it truly parallel
        from core.voice.wake_word import WakeWordDetector
        temp_detector = WakeWordDetector()
        temp_detector.initialize()
        
        # Small grace period to avoid catching self-voice tail
        time.sleep(0.5)

        while not self.interrupted.is_set() and self.is_running:
            # Check for wake word in parallel
            if temp_detector.listen_for_wake_word(self.audio_queue):
                logger.info("🚨 INTERRUPTION DETECTED via Wake Word!")
                self.interrupted.set()
                self.tts_engine.stop()
                break
            time.sleep(0.1)


    def stop(self):
        """Clean shutdown of the audio stack."""
        logger.info("Shutting down Voice Manager...")
        self.is_running = False
        if self.wake_detector:
            self.wake_detector.stop()
        if self.mic_stream:
            self.mic_stream.stop()
            self.mic_stream.close()
            
        logger.info("Voice Manager stopped.")
