"""Unit tests for Session State Manager."""
import unittest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python" / "src"))

from session_state import SessionStateManager


class TestSessionStateManager(unittest.TestCase):
    """Test SessionStateManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.ssm = SessionStateManager("test_shared_memory")
    
    def tearDown(self):
        """Clean up after tests."""
        self.ssm.close()
    
    def test_init_shared_state(self):
        """Test shared memory initialization."""
        result = self.ssm.init_shared_state(create=True)
        self.assertTrue(result)
        self.assertIsNotNone(self.ssm.memory)
    
    def test_update_harmonic_context(self):
        """Test updating harmonic context."""
        self.ssm.init_shared_state(create=True)
        harmonic_data = np.array([0.1, 0.2, 0.3, 0.4] * 32, dtype=np.float32)
        self.ssm.update_harmonic_context(harmonic_data)
        # Would verify in shared memory if we had read access
    
    def test_update_rhythmic_context(self):
        """Test updating rhythmic context."""
        self.ssm.init_shared_state(create=True)
        rhythmic_data = np.array([0.5, 0.6, 0.7, 0.8] * 16, dtype=np.float32)
        self.ssm.update_rhythmic_context(rhythmic_data)
    
    def test_set_cloud_stem_ready(self):
        """Test setting cloud stem ready flag."""
        self.ssm.init_shared_state(create=True)
        self.ssm.set_cloud_stem_ready("/path/to/stem.wav")
        commands = self.ssm.get_sync_commands()
        self.assertTrue(commands.get('cloud_stem_ready', False))


if __name__ == '__main__':
    unittest.main()
