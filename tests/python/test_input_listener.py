"""Unit tests for Input Listener."""
import unittest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python" / "src"))

from input_listener import InputListener
from session_state import SessionStateManager


class TestInputListener(unittest.TestCase):
    """Test InputListener."""
    
    def setUp(self):
        """Set up test fixtures."""
        config = {
            'audio': {'sample_rate': 44100},
            'input_processing': {
                'guitar': {
                    'analysis_window_ms': 100,
                    'min_activity_threshold': 0.01
                },
                'voice': {
                    'activity_threshold': 0.05,
                    'command_timeout_ms': 2000,
                    'silence_detection': True
                }
            }
        }
        ssm = SessionStateManager("test_shared_memory")
        ssm.init_shared_state(create=True)
        self.listener = InputListener(ssm, config)
    
    def test_has_audio_activity(self):
        """Test audio activity detection."""
        # Test with active audio
        active_buffer = np.random.randn(1024).astype(np.float32) * 0.1
        self.assertTrue(self.listener.has_audio_activity(active_buffer))
        
        # Test with silent audio
        silent_buffer = np.zeros(1024, dtype=np.float32)
        self.assertFalse(self.listener.has_audio_activity(silent_buffer))
    
    def test_has_voice_activity(self):
        """Test voice activity detection."""
        # Test with voice
        voice_buffer = np.random.randn(1024).astype(np.float32) * 0.1
        self.assertTrue(self.listener.has_voice_activity(voice_buffer))
        
        # Test with silence
        silent_buffer = np.zeros(1024, dtype=np.float32)
        self.assertFalse(self.listener.has_voice_activity(silent_buffer))
    
    def test_analyze_harmonic_content(self):
        """Test harmonic content analysis."""
        # Generate test audio (sine wave)
        sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        
        result = self.listener.analyze_harmonic_content(audio)
        self.assertIsInstance(result, dict)
        # Would verify specific values in production


if __name__ == '__main__':
    unittest.main()
