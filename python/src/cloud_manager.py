"""
Cloud Manager - Manages cloud audio stem generation (mock for MVP).
"""
import numpy as np
import soundfile as sf
import time
import threading
import os
from typing import Optional, Dict, Any
from .session_state import SessionStateManager


class CloudManager:
    """Manages cloud audio stem generation and download."""
    
    def __init__(self, ssm: SessionStateManager, config: Dict[str, Any]):
        self.ssm = ssm
        self.config = config
        self.running = False
        self.thread = None
        
        # Configuration
        self.mock_generation_time = config['cloud_manager']['mock_generation_time']
        self.timeout_seconds = config['cloud_manager']['timeout_seconds']
        self.stem_directory = config['cloud_manager']['stem_directory']
        self.sample_rate = config['audio']['sample_rate']
        self.loop_length_bars = config['session']['default_loop_length_bars']
        self.tempo = config['session']['default_tempo']
        
        # State
        self.current_request = None
        self.generation_start_time = None
        self.last_loop_timer = 0.0
        
        # Ensure stem directory exists
        os.makedirs(self.stem_directory, exist_ok=True)
    
    def package_context(self) -> Dict[str, Any]:
        """Package session context for cloud generation."""
        sync_commands = self.ssm.get_sync_commands()
        
        return {
            'key': 0.0,  # Would read from SSM
            'tempo': self.tempo,
            'loop_length_bars': self.loop_length_bars,
            'vibe': 'default',  # Would read from SSM
            'harmonic_context': [],  # Would read from SSM
            'rhythmic_context': [],  # Would read from SSM
        }
    
    def mock_generate_stem(self, context: Dict[str, Any]) -> Optional[str]:
        """Generate mock audio stem (simulates cloud generation)."""
        try:
            # Calculate duration in samples
            beats_per_bar = 4
            seconds_per_bar = (60.0 / context['tempo']) * beats_per_bar
            duration_seconds = seconds_per_bar * context['loop_length_bars']
            num_samples = int(duration_seconds * self.sample_rate)
            
            # Generate audio (simple patterns)
            audio = np.zeros((num_samples,), dtype=np.float32)
            
            # Generate bass line (sine wave)
            bass_freq = 60.0  # C2
            t = np.linspace(0, duration_seconds, num_samples)
            bass = np.sin(2 * np.pi * bass_freq * t) * 0.3
            
            # Generate drum pattern (impulses)
            beats_per_bar = 4
            total_beats = context['loop_length_bars'] * beats_per_bar
            beat_samples = int(self.sample_rate * (60.0 / context['tempo']))
            
            drums = np.zeros_like(audio)
            for beat in range(total_beats):
                if beat % 4 == 0 or beat % 4 == 2:  # Kick on 1 and 3
                    idx = beat * beat_samples
                    if idx < len(drums):
                        drums[idx:idx+100] = np.random.randn(100) * 0.2
                if beat % 4 == 1 or beat % 4 == 3:  # Snare on 2 and 4
                    idx = beat * beat_samples
                    if idx < len(drums):
                        drums[idx:idx+200] = np.random.randn(200) * 0.15
            
            # Generate pad (chord)
            pad_freq = 261.63  # C4
            pad = np.sin(2 * np.pi * pad_freq * t) * 0.1
            
            # Mix
            audio = bass + drums + pad
            
            # Normalize
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val * 0.8
            
            # Generate filename
            timestamp = int(time.time())
            filename = f"cloud_stem_{timestamp}.wav"
            filepath = os.path.join(self.stem_directory, filename)
            
            # Save as WAV
            sf.write(filepath, audio, self.sample_rate)
            
            print(f"Generated mock cloud stem: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"Error generating mock stem: {e}")
            return None
    
    def run_cloud_loop(self):
        """Main cloud generation loop."""
        print("Cloud manager started")
        
        while self.running:
            try:
                # Check sync commands
                sync_commands = self.ssm.get_sync_commands()
                loop_timer = sync_commands.get('loop_timer', 0.0)
                cloud_stem_ready = sync_commands.get('cloud_stem_ready', False)
                
                # Detect new loop cycle (when loop_timer resets)
                loop_started = (loop_timer < 0.1 and self.last_loop_timer > 0.5)
                
                # Start generation at loop start if not already generating
                if loop_started and self.current_request is None:
                    # Package context
                    context = self.package_context()
                    
                    # Start generation
                    self.current_request = context
                    self.generation_start_time = time.time()
                    print("Starting cloud stem generation...")
                
                # Check if generation is complete
                if self.current_request is not None:
                    elapsed = time.time() - self.generation_start_time
                    
                    if elapsed >= self.mock_generation_time:
                        # Generate stem
                        stem_path = self.mock_generate_stem(self.current_request)
                        
                        if stem_path:
                            # Update SSM
                            self.ssm.set_cloud_stem_ready(stem_path)
                            print(f"Cloud stem ready: {stem_path}")
                        else:
                            print("Failed to generate cloud stem")
                        
                        # Reset request
                        self.current_request = None
                        self.generation_start_time = None
                    
                    # Check timeout
                    elif elapsed > self.timeout_seconds:
                        print("Cloud generation timeout")
                        self.current_request = None
                        self.generation_start_time = None
                
                # Update last loop timer
                self.last_loop_timer = loop_timer
                
                # Sleep to avoid CPU spinning
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in cloud loop: {e}")
                time.sleep(0.5)
    
    def start(self):
        """Start the cloud manager thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.run_cloud_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the cloud manager thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
