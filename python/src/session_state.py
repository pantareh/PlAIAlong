"""
Session State Manager (SSM) - Central state coordination using shared memory.
"""
import mmap
import struct
import ctypes
import os
from typing import Optional, Dict, Any
import numpy as np


class SessionStateManager:
    """Manages shared memory session state between Python and C++."""
    
    # Structure sizes (must match C struct)
    MAX_AUDIO_BUFFER_SIZE = 2048
    MAX_STEM_PATH_LENGTH = 512
    
    def __init__(self, shared_memory_name: str = "plaialong_shared_memory"):
        self.shared_memory_name = shared_memory_name
        self.memory = None
        self.size = 0
        self.is_owner = False
        
    def init_shared_state(self, create: bool = False) -> bool:
        """Initialize shared memory (create or attach)."""
        try:
            # Calculate size of SessionState struct
            # This should match the C struct size
            size = (
                4 * 8 +  # floats and doubles: current_key, tempo, loop_timer (8 bytes each)
                4 * 4 +  # ints: loop_length_bars, cloud_stem_ready, fallback_active, system_running
                512 +    # cloud_stem_path
                128 * 4 + # harmonic_data (128 floats)
                64 * 4 +  # rhythmic_data (64 floats)
                4 * 2 +   # harmonic_data_size, rhythmic_data_size
                # AudioBuffers struct
                2048 * 4 * 2 +  # guitar_channel, voice_channel (each 2048 floats)
                4 * 3 +   # buffer_size, sample_rate, frame_counter
                4 * 2 +   # guitar_ready, voice_ready
                8         # sync_timestamp
            )
            self.size = size
            
            if create:
                # Create shared memory
                if os.name == 'nt':  # Windows
                    # On Windows, we'll use a file mapping approach
                    # For now, use a simpler approach with mmap
                    self.memory = mmap.mmap(-1, size, tagname=shared_memory_name, access=mmap.ACCESS_WRITE)
                else:  # Linux/Mac
                    # Create shared memory object
                    fd = os.open(f"/dev/shm/{shared_memory_name}", os.O_CREAT | os.O_RDWR, 0o666)
                    os.ftruncate(fd, size)
                    self.memory = mmap.mmap(fd, size, access=mmap.ACCESS_WRITE)
                    os.close(fd)
                self.is_owner = True
                # Initialize to zero
                self.memory[:] = b'\x00' * size
            else:
                # Attach to existing shared memory
                if os.name == 'nt':  # Windows
                    self.memory = mmap.mmap(-1, size, tagname=shared_memory_name, access=mmap.ACCESS_WRITE)
                else:  # Linux/Mac
                    fd = os.open(f"/dev/shm/{shared_memory_name}", os.O_RDWR)
                    self.memory = mmap.mmap(fd, size, access=mmap.ACCESS_WRITE)
                    os.close(fd)
                self.is_owner = False
            
            return True
        except Exception as e:
            print(f"Error initializing shared memory: {e}")
            return False
    
    def close(self):
        """Close shared memory."""
        if self.memory:
            self.memory.close()
            self.memory = None
            if self.is_owner and os.name != 'nt':
                try:
                    os.unlink(f"/dev/shm/{self.shared_memory_name}")
                except:
                    pass
    
    def _read_float(self, offset: int) -> float:
        """Read float from memory at offset."""
        return struct.unpack('f', self.memory[offset:offset+4])[0]
    
    def _write_float(self, offset: int, value: float):
        """Write float to memory at offset."""
        self.memory[offset:offset+4] = struct.pack('f', value)
    
    def _read_double(self, offset: int) -> float:
        """Read double from memory at offset."""
        return struct.unpack('d', self.memory[offset:offset+8])[0]
    
    def _write_double(self, offset: int, value: float):
        """Write double to memory at offset."""
        self.memory[offset:offset+8] = struct.pack('d', value)
    
    def _read_int(self, offset: int) -> int:
        """Read int from memory at offset."""
        return struct.unpack('i', self.memory[offset:offset+4])[0]
    
    def _write_int(self, offset: int, value: int):
        """Write int to memory at offset."""
        self.memory[offset:offset+4] = struct.pack('i', value)
    
    def _read_string(self, offset: int, length: int) -> str:
        """Read string from memory at offset."""
        data = self.memory[offset:offset+length]
        # Find null terminator
        null_pos = data.find(b'\x00')
        if null_pos >= 0:
            data = data[:null_pos]
        return data.decode('utf-8', errors='ignore')
    
    def _write_string(self, offset: int, value: str, length: int):
        """Write string to memory at offset."""
        encoded = value.encode('utf-8')[:length-1]
        self.memory[offset:offset+len(encoded)] = encoded
        self.memory[offset+len(encoded)] = 0  # Null terminator
    
    def update_harmonic_context(self, harmonic_data: np.ndarray):
        """Update harmonic analysis data in SSM."""
        if self.memory is None:
            return
        # Offset for harmonic_data (after floats, ints, and path)
        offset = 4 * 8 + 4 * 4 + 512  # Skip to harmonic_data
        size = min(len(harmonic_data), 128)
        for i in range(size):
            self._write_float(offset + i * 4, float(harmonic_data[i]))
        # Update size
        self._write_int(offset + 128 * 4, size)
    
    def update_rhythmic_context(self, rhythmic_data: np.ndarray):
        """Update rhythmic analysis data in SSM."""
        if self.memory is None:
            return
        # Offset for rhythmic_data (after harmonic_data)
        offset = 4 * 8 + 4 * 4 + 512 + 128 * 4 + 4  # Skip to rhythmic_data
        size = min(len(rhythmic_data), 64)
        for i in range(size):
            self._write_float(offset + i * 4, float(rhythmic_data[i]))
        # Update size
        self._write_int(offset + 64 * 4, size)
    
    def set_cloud_stem_ready(self, path: str):
        """Signal that cloud stem is ready."""
        if self.memory is None:
            return
        # Write path
        path_offset = 4 * 8 + 4 * 4  # After floats and ints
        self._write_string(path_offset, path, self.MAX_STEM_PATH_LENGTH)
        # Set ready flag
        self._write_int(4 * 8 + 4 * 3, 1)  # cloud_stem_ready
    
    def get_sync_commands(self) -> Dict[str, Any]:
        """Read sync instructions for C++."""
        if self.memory is None:
            return {}
        
        return {
            'loop_timer': self._read_double(4 * 8 + 4 * 2),  # After current_key and tempo
            'loop_length_bars': self._read_int(4 * 8 + 4 * 2 + 8),
            'cloud_stem_ready': self._read_int(4 * 8 + 4 * 3) == 1,
            'cloud_stem_path': self._read_string(4 * 8 + 4 * 4, self.MAX_STEM_PATH_LENGTH),
        }
    
    def read_guitar_buffer(self) -> Optional[np.ndarray]:
        """Read guitar audio buffer from shared memory."""
        if self.memory is None:
            return None
        
        # Calculate offset to audio_inputs.guitar_channel
        # After all the session state fields
        audio_offset = (
            4 * 8 +  # floats/doubles
            4 * 4 +  # ints
            512 +    # path
            128 * 4 + # harmonic_data
            64 * 4 +  # rhythmic_data
            4 * 2     # sizes
        )
        
        buffer_size = self._read_int(audio_offset + 2048 * 4 * 2)  # buffer_size field
        if buffer_size == 0 or buffer_size > self.MAX_AUDIO_BUFFER_SIZE:
            return None
        
        # Read guitar channel
        guitar_data = np.frombuffer(
            self.memory[audio_offset:audio_offset + buffer_size * 4],
            dtype=np.float32
        ).copy()
        
        # Clear ready flag
        self._write_int(audio_offset + 2048 * 4 * 2 + 4 * 2, 0)  # guitar_ready = 0
        
        return guitar_data
    
    def read_voice_buffer(self) -> Optional[np.ndarray]:
        """Read voice audio buffer from shared memory."""
        if self.memory is None:
            return None
        
        # Calculate offset to audio_inputs.voice_channel
        audio_offset = (
            4 * 8 + 4 * 4 + 512 + 128 * 4 + 64 * 4 + 4 * 2 +  # Before audio_inputs
            2048 * 4  # Skip guitar_channel
        )
        
        buffer_size = self._read_int(audio_offset + 2048 * 4)  # buffer_size field
        if buffer_size == 0 or buffer_size > self.MAX_AUDIO_BUFFER_SIZE:
            return None
        
        # Read voice channel
        voice_data = np.frombuffer(
            self.memory[audio_offset:audio_offset + buffer_size * 4],
            dtype=np.float32
        ).copy()
        
        # Clear ready flag
        self._write_int(audio_offset + 2048 * 4 + 4 * 2 + 4, 0)  # voice_ready = 0
        
        return voice_data
    
    def update_musical_context(self, key: float, tempo: float):
        """Update musical context (key and tempo)."""
        if self.memory is None:
            return
        self._write_float(0, key)  # current_key
        self._write_float(4, tempo)  # tempo
    
    def set_system_running(self, running: bool):
        """Set system running flag."""
        if self.memory is None:
            return
        # Calculate offset to system_running
        offset = 4 * 8 + 4 * 4 + 512 + 128 * 4 + 64 * 4 + 4 * 2 + 2048 * 4 * 2 + 4 * 5
        self._write_int(offset, 1 if running else 0)
