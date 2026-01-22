"""
Input & Command Listener - Analyzes audio input and parses voice commands.
"""
import numpy as np
import librosa
import whisper
import time
import threading
from typing import Optional, Dict, Any
from .session_state import SessionStateManager


class InputListener:
    """Listens to audio input, analyzes harmonic/rhythmic content, and parses voice commands."""
    
    def __init__(self, ssm: SessionStateManager, config: Dict[str, Any]):
        self.ssm = ssm
        self.config = config
        self.running = False
        self.thread = None
        
        # Audio analysis parameters
        self.sample_rate = config['audio']['sample_rate']
        self.analysis_window_ms = config['input_processing']['guitar']['analysis_window_ms']
        self.min_activity_threshold = config['input_processing']['guitar']['min_activity_threshold']
        self.voice_threshold = config['input_processing']['voice']['activity_threshold']
        
        # Voice command processing
        self.voice_model = None
        self.voice_buffer = []
        self.command_timeout_ms = config['input_processing']['voice']['command_timeout_ms']
        self.last_voice_time = 0
        
        # Initialize Whisper for voice commands (lazy load)
        self._init_voice_model()
        
        # Analysis state
        self.tempo_history = []
        self.key_history = []
        
    def _init_voice_model(self):
        """Initialize Whisper model for voice commands (lazy loading)."""
        try:
            # Use base model for faster processing
            self.voice_model = whisper.load_model("base")
            print("Voice command model loaded")
        except Exception as e:
            print(f"Warning: Could not load Whisper model: {e}")
            self.voice_model = None
    
    def has_audio_activity(self, buffer: np.ndarray) -> bool:
        """Detect if audio buffer has significant activity."""
        if buffer is None or len(buffer) == 0:
            return False
        rms = np.sqrt(np.mean(buffer**2))
        return rms > self.min_activity_threshold
    
    def has_voice_activity(self, buffer: np.ndarray) -> bool:
        """Detect if voice channel has actual voice input."""
        if buffer is None or len(buffer) == 0:
            return False
        rms = np.sqrt(np.mean(buffer**2))
        return rms > self.voice_threshold
    
    def analyze_harmonic_content(self, buffer: np.ndarray) -> Dict[str, Any]:
        """Analyze harmonic content (chord detection, key estimation)."""
        if buffer is None or len(buffer) < 1024:
            return {}
        
        try:
            # Convert to mono if needed
            if len(buffer.shape) > 1:
                buffer = np.mean(buffer, axis=0)
            
            # Estimate key
            chroma = librosa.feature.chroma_stft(y=buffer, sr=self.sample_rate)
            chroma_mean = np.mean(chroma, axis=1)
            
            # Find dominant key (simplified)
            key_profiles = librosa.harmonic.key_profiles()
            key_scores = []
            for profile in key_profiles:
                score = np.dot(chroma_mean, profile)
                key_scores.append(score)
            
            estimated_key = np.argmax(key_scores)
            key_confidence = np.max(key_scores)
            
            # Chord detection
            chroma_frame = np.mean(chroma, axis=1)
            # Simple chord detection (can be enhanced)
            chord_estimate = self._estimate_chord(chroma_frame)
            
            return {
                'key': float(estimated_key),
                'key_confidence': float(key_confidence),
                'chroma': chroma_mean.tolist(),
                'chord': chord_estimate
            }
        except Exception as e:
            print(f"Error in harmonic analysis: {e}")
            return {}
    
    def _estimate_chord(self, chroma: np.ndarray) -> str:
        """Simple chord estimation from chroma vector."""
        # Normalize
        chroma_norm = chroma / (np.sum(chroma) + 1e-6)
        
        # Find dominant notes
        threshold = 0.1
        active_notes = np.where(chroma_norm > threshold)[0]
        
        if len(active_notes) == 0:
            return "N"
        
        # Simple major/minor detection
        root = int(active_notes[0])
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        # Check for major third (4 semitones)
        if (root + 4) % 12 in active_notes:
            return f"{note_names[root]}maj"
        # Check for minor third (3 semitones)
        elif (root + 3) % 12 in active_notes:
            return f"{note_names[root]}min"
        else:
            return f"{note_names[root]}"
    
    def analyze_rhythmic_content(self, buffer: np.ndarray) -> Dict[str, Any]:
        """Analyze rhythmic content (tempo, beat tracking)."""
        if buffer is None or len(buffer) < 2048:
            return {}
        
        try:
            # Convert to mono if needed
            if len(buffer.shape) > 1:
                buffer = np.mean(buffer, axis=0)
            
            # Tempo estimation
            tempo, beats = librosa.beat.beat_track(
                y=buffer,
                sr=self.sample_rate,
                units='time'
            )
            
            # Update tempo history
            if tempo > 0:
                self.tempo_history.append(tempo)
                if len(self.tempo_history) > 10:
                    self.tempo_history.pop(0)
            
            # Average tempo
            avg_tempo = np.mean(self.tempo_history) if self.tempo_history else 120.0
            
            # Beat positions
            beat_times = beats if len(beats) > 0 else []
            
            return {
                'tempo': float(avg_tempo),
                'instant_tempo': float(tempo),
                'beat_times': [float(t) for t in beat_times[:64]],  # Limit to 64
                'beat_count': len(beat_times)
            }
        except Exception as e:
            print(f"Error in rhythmic analysis: {e}")
            return {}
    
    def parse_voice_command(self, audio: np.ndarray) -> Optional[str]:
        """Parse voice command from audio buffer using Whisper."""
        if self.voice_model is None or audio is None or len(audio) == 0:
            return None
        
        try:
            # Accumulate voice buffer
            self.voice_buffer.extend(audio.tolist())
            
            # Check if we have enough audio (at least 1 second)
            min_samples = self.sample_rate
            if len(self.voice_buffer) < min_samples:
                return None
            
            # Process when we have enough audio or timeout
            current_time = time.time() * 1000
            time_since_voice = current_time - self.last_voice_time
            
            if len(self.voice_buffer) >= min_samples * 2 or time_since_voice > self.command_timeout_ms:
                # Convert to numpy array
                audio_array = np.array(self.voice_buffer, dtype=np.float32)
                
                # Normalize
                if np.max(np.abs(audio_array)) > 0:
                    audio_array = audio_array / np.max(np.abs(audio_array))
                
                # Transcribe
                result = self.voice_model.transcribe(
                    audio_array,
                    language="en",
                    task="transcribe"
                )
                
                text = result["text"].strip().lower()
                
                # Clear buffer
                self.voice_buffer = []
                self.last_voice_time = current_time
                
                # Parse command
                return self._parse_command(text)
            
            return None
        except Exception as e:
            print(f"Error in voice command parsing: {e}")
            self.voice_buffer = []
            return None
    
    def _parse_command(self, text: str) -> Optional[str]:
        """Parse text into command."""
        if not text:
            return None
        
        # Simple command parsing
        text_lower = text.lower()
        
        # Genre/vibe commands
        if "jazz" in text_lower:
            return "set_vibe:jazz"
        elif "rock" in text_lower:
            return "set_vibe:rock"
        elif "blues" in text_lower:
            return "set_vibe:blues"
        elif "stop" in text_lower or "pause" in text_lower:
            return "stop"
        elif "start" in text_lower or "play" in text_lower:
            return "start"
        elif "faster" in text_lower or "speed up" in text_lower:
            return "tempo_up"
        elif "slower" in text_lower or "slow down" in text_lower:
            return "tempo_down"
        
        return None
    
    def process_command(self, command: str):
        """Process a parsed command."""
        if not command:
            return
        
        print(f"Processing command: {command}")
        
        # Update SSM based on command
        if command.startswith("set_vibe:"):
            vibe = command.split(":")[1]
            # Would update vibe in SSM
            print(f"Setting vibe to: {vibe}")
        elif command == "stop":
            self.ssm.set_system_running(False)
        elif command == "start":
            self.ssm.set_system_running(True)
        elif command == "tempo_up":
            # Would adjust tempo
            pass
        elif command == "tempo_down":
            # Would adjust tempo
            pass
    
    def run_listener_loop(self):
        """Main processing loop."""
        print("Input listener started")
        
        while self.running:
            try:
                # Read guitar buffer
                guitar_buffer = self.ssm.read_guitar_buffer()
                if guitar_buffer is not None and self.has_audio_activity(guitar_buffer):
                    # Analyze harmonic content
                    harmonic_data = self.analyze_harmonic_content(guitar_buffer)
                    if harmonic_data:
                        # Update SSM
                        if 'chroma' in harmonic_data:
                            chroma_array = np.array(harmonic_data['chroma'], dtype=np.float32)
                            self.ssm.update_harmonic_context(chroma_array)
                        
                        # Update key and tempo
                        if 'key' in harmonic_data:
                            self.ssm.update_musical_context(
                                harmonic_data['key'],
                                harmonic_data.get('tempo', 120.0)
                            )
                    
                    # Analyze rhythmic content
                    rhythmic_data = self.analyze_rhythmic_content(guitar_buffer)
                    if rhythmic_data:
                        if 'tempo' in rhythmic_data:
                            # Update tempo in SSM
                            current_key = 0.0  # Would read from SSM
                            self.ssm.update_musical_context(
                                current_key,
                                rhythmic_data['tempo']
                            )
                        
                        # Update rhythmic data
                        if 'beat_times' in rhythmic_data:
                            beat_array = np.array(rhythmic_data['beat_times'], dtype=np.float32)
                            self.ssm.update_rhythmic_context(beat_array)
                
                # Read voice buffer
                voice_buffer = self.ssm.read_voice_buffer()
                if voice_buffer is not None and self.has_voice_activity(voice_buffer):
                    self.last_voice_time = time.time() * 1000
                    command = self.parse_voice_command(voice_buffer)
                    if command:
                        self.process_command(command)
                
                # Small sleep to avoid CPU spinning
                time.sleep(0.01)
                
            except Exception as e:
                print(f"Error in listener loop: {e}")
                time.sleep(0.1)
    
    def start(self):
        """Start the listener thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.run_listener_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the listener thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
