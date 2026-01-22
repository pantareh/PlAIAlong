"""
Local Generator - Generates MIDI patterns using MusicTransformer and sends to C++.
"""
import torch
import mido
import numpy as np
import time
import threading
import os
import sys
import struct
from typing import Optional, Dict, Any, List
from .session_state import SessionStateManager


class LocalGenerator:
    """Generates complementary MIDI patterns using MusicTransformer."""
    
    def __init__(self, ssm: SessionStateManager, config: Dict[str, Any]):
        self.ssm = ssm
        self.config = config
        self.running = False
        self.thread = None
        
        # Model parameters
        self.model_path = config['local_generator']['model_path']
        self.instruments = config['local_generator']['instruments']
        self.generation_length_bars = config['local_generator']['generation_length_bars']
        self.ipc_pipe_name = config['local_generator']['ipc_pipe_name']
        
        # Model state
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Generation state
        self.current_midi = None
        self.fallback_active = False
        self.last_generation_time = 0
        self.generation_interval = 8.0  # Generate every 8 bars (at loop boundary)
        
        # IPC pipe
        self.pipe = None
        
        # Initialize model (lazy loading)
        self._init_model()
        self._init_ipc()
    
    def _init_model(self):
        """Initialize MusicTransformer model."""
        try:
            # For MVP, we'll use a simplified approach
            # In production, this would load the actual MusicTransformer model
            print("LocalGenerator: Using simplified MIDI generation for MVP")
            print("Note: Full MusicTransformer integration requires model checkpoint")
            self.model = None  # Placeholder
        except Exception as e:
            print(f"Warning: Could not load MusicTransformer model: {e}")
            self.model = None
    
    def _init_ipc(self):
        """Initialize IPC pipe for MIDI communication."""
        try:
            if sys.platform == 'win32':
                try:
                    import win32pipe
                    import win32file
                    # Create named pipe
                    self.pipe_name = f"\\\\.\\pipe\\{self.ipc_pipe_name}"
                    # Pipe will be created when needed
                    self.pipe_available = True
                except ImportError:
                    print("Warning: pywin32 not available, IPC disabled")
                    self.pipe_available = False
            else:
                # Unix named pipe
                pipe_path = f"/tmp/{self.ipc_pipe_name}"
                if not os.path.exists(pipe_path):
                    os.mkfifo(pipe_path)
                self.pipe_path = pipe_path
                self.pipe_available = True
        except Exception as e:
            print(f"Warning: Could not initialize IPC: {e}")
            self.pipe_available = False
    
    def _send_midi_to_cpp(self, midi_file: mido.MidiFile) -> bool:
        """Send MIDI data to C++ via IPC."""
        if not self.pipe_available:
            return False
        
        try:
            # Convert MIDI to binary format
            midi_bytes = midi_file.save()
            
            if sys.platform == 'win32':
                try:
                    import win32pipe
                    import win32file
                    try:
                        # Open named pipe
                        handle = win32file.CreateFile(
                            self.pipe_name,
                            win32file.GENERIC_WRITE,
                            0,
                            None,
                            win32file.OPEN_EXISTING,
                            0,
                            None
                        )
                        
                        # Write message header
                        header = struct.pack('IIQ', 1, len(midi_bytes), int(time.time() * 1000))
                        win32file.WriteFile(handle, header, None)
                        
                        # Write MIDI data
                        win32file.WriteFile(handle, midi_bytes, None)
                        
                        win32file.CloseHandle(handle)
                        return True
                    except Exception as e:
                        print(f"Error writing to pipe: {e}")
                        return False
                except ImportError:
                    return False
            else:
                # Unix named pipe
                try:
                    with open(self.pipe_path, 'wb') as f:
                        # Write header
                        header = struct.pack('IIQ', 1, len(midi_bytes), int(time.time() * 1000))
                        f.write(header)
                        f.write(midi_bytes)
                    return True
                except Exception as e:
                    print(f"Error writing to pipe: {e}")
                    return False
        except Exception as e:
            print(f"Error sending MIDI: {e}")
            return False
    
    def generate_midi_pattern(self, context: Dict[str, Any], instrument: str) -> Optional[mido.MidiFile]:
        """Generate MIDI pattern for given instrument and context."""
        try:
            # For MVP, generate simple patterns
            # In production, this would use MusicTransformer
            
            key = context.get('key', 0)
            tempo = context.get('tempo', 120)
            bars = self.generation_length_bars
            
            # Create MIDI file
            mid = mido.MidiFile()
            track = mido.MidiTrack()
            mid.tracks.append(track)
            
            # Set tempo
            tempo_microseconds = int(60000000 / tempo)
            track.append(mido.MetaMessage('set_tempo', tempo=tempo_microseconds))
            
            # Generate pattern based on instrument
            if instrument == "bass":
                self._generate_bass_pattern(track, key, tempo, bars)
            elif instrument == "drums":
                self._generate_drum_pattern(track, tempo, bars)
            elif instrument == "pad":
                self._generate_pad_pattern(track, key, tempo, bars)
            
            # End track
            track.append(mido.MetaMessage('end_of_track'))
            
            return mid
            
        except Exception as e:
            print(f"Error generating MIDI pattern: {e}")
            return None
    
    def _generate_bass_pattern(self, track: mido.MidiTrack, key: int, tempo: float, bars: int):
        """Generate simple bass pattern."""
        ticks_per_beat = track.ticks_per_beat if hasattr(track, 'ticks_per_beat') else 480
        beats_per_bar = 4
        ticks_per_bar = ticks_per_beat * beats_per_bar
        
        # Root note (C = 60)
        root_note = 36 + int(key)  # Bass range
        
        # Simple quarter note pattern
        for bar in range(bars):
            for beat in range(beats_per_bar):
                # Play root on beat 1, fifth on beat 3
                if beat == 0:
                    note = root_note
                elif beat == 2:
                    note = root_note + 7  # Fifth
                else:
                    continue
                
                # Note on
                track.append(mido.Message('note_on', channel=0, note=note, velocity=80, time=0))
                # Note off after quarter note
                track.append(mido.Message('note_off', channel=0, note=note, velocity=0, time=ticks_per_beat))
    
    def _generate_drum_pattern(self, track: mido.MidiTrack, tempo: float, bars: int):
        """Generate simple drum pattern."""
        ticks_per_beat = track.ticks_per_beat if hasattr(track, 'ticks_per_beat') else 480
        beats_per_bar = 4
        
        # Drum notes: Kick=36, Snare=38, HiHat=42
        for bar in range(bars):
            for beat in range(beats_per_bar):
                # Kick on 1 and 3
                if beat == 0 or beat == 2:
                    track.append(mido.Message('note_on', channel=9, note=36, velocity=100, time=0))
                    track.append(mido.Message('note_off', channel=9, note=36, velocity=0, time=ticks_per_beat // 2))
                
                # Snare on 2 and 4
                if beat == 1 or beat == 3:
                    track.append(mido.Message('note_on', channel=9, note=38, velocity=80, time=0))
                    track.append(mido.Message('note_off', channel=9, note=38, velocity=0, time=ticks_per_beat // 2))
                
                # HiHat on all beats
                track.append(mido.Message('note_on', channel=9, note=42, velocity=60, time=0))
                track.append(mido.Message('note_off', channel=9, note=42, velocity=0, time=ticks_per_beat // 4))
    
    def _generate_pad_pattern(self, track: mido.MidiTrack, key: int, tempo: float, bars: int):
        """Generate simple pad pattern."""
        ticks_per_beat = track.ticks_per_beat if hasattr(track, 'ticks_per_beat') else 480
        beats_per_bar = 4
        ticks_per_bar = ticks_per_beat * beats_per_bar
        
        # Root note (C = 60)
        root_note = 48 + int(key)  # Mid range
        
        # Simple chord pattern (major triad)
        chord_notes = [root_note, root_note + 4, root_note + 7]  # Root, third, fifth
        
        # Play chord every bar
        for bar in range(bars):
            # Note on for all chord notes
            for note in chord_notes:
                track.append(mido.Message('note_on', channel=1, note=note, velocity=60, time=0))
            
            # Hold for whole bar
            for note in chord_notes:
                track.append(mido.Message('note_off', channel=1, note=note, velocity=0, time=ticks_per_bar))
    
    def apply_fallback_variation(self, midi: mido.MidiFile) -> mido.MidiFile:
        """Apply minimal variation to MIDI for fallback mode."""
        # Create a copy
        new_midi = mido.MidiFile()
        
        for track in midi.tracks:
            new_track = mido.MidiTrack()
            for msg in track:
                if msg.type == 'note_on':
                    # Slight velocity variation
                    new_velocity = min(127, max(1, msg.velocity + np.random.randint(-5, 5)))
                    new_msg = msg.copy(velocity=new_velocity)
                    new_track.append(new_msg)
                else:
                    new_track.append(msg.copy())
            new_midi.tracks.append(new_track)
        
        return new_midi
    
    def run_generator_loop(self):
        """Main generation loop."""
        print("Local generator started")
        
        while self.running:
            try:
                # Check if we need to generate new pattern
                sync_commands = self.ssm.get_sync_commands()
                loop_timer = sync_commands.get('loop_timer', 0.0)
                loop_length = sync_commands.get('loop_length_bars', 8)
                
                # Check if at loop boundary
                current_time = time.time()
                time_since_generation = current_time - self.last_generation_time
                
                # Generate at loop start or after interval
                should_generate = (
                    loop_timer < 0.1 or  # At loop start
                    time_since_generation > self.generation_interval
                )
                
                if should_generate and not self.fallback_active:
                    # Get context from SSM
                    # For MVP, use default context
                    context = {
                        'key': 0.0,  # Would read from SSM
                        'tempo': 120.0,  # Would read from SSM
                    }
                    
                    # Generate MIDI for each instrument
                    for instrument in self.instruments:
                        midi = self.generate_midi_pattern(context, instrument)
                        if midi:
                            # Send to C++
                            if self._send_midi_to_cpp(midi):
                                print(f"Generated and sent {instrument} pattern")
                            self.current_midi = midi
                    
                    self.last_generation_time = current_time
                
                # Check for fallback mode
                if sync_commands.get('fallback_active', False) and self.current_midi:
                    # Apply variation and resend
                    varied_midi = self.apply_fallback_variation(self.current_midi)
                    self._send_midi_to_cpp(varied_midi)
                    self.fallback_active = True
                else:
                    self.fallback_active = False
                
                # Sleep to avoid CPU spinning
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in generator loop: {e}")
                time.sleep(0.5)
    
    def start(self):
        """Start the generator thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.run_generator_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the generator thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
