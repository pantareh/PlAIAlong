"""Test text-to-track generation using actual services."""
import unittest
import numpy as np
import soundfile as sf
import os
import tempfile
import shutil
from pathlib import Path

from src.local_generator import LocalGenerator
from src.cloud_manager import CloudManager
from src.session_state import SessionStateManager
from src.utils import parse_text_instruction


class TestTextToTrack(unittest.TestCase):
    """Test text-to-track generation using actual services."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_rate = 44100
        self.output_dir = Path(__file__).parent / "generated_tracks"
        self.output_dir.mkdir(exist_ok=True)
        
        # Create temporary config for services
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = {
            'audio': {
                'sample_rate': self.sample_rate,
                'shared_memory_name': 'test_shared_memory'
            },
            'session': {
                'default_tempo': 120,
                'default_loop_length_bars': 8
            },
            'local_generator': {
                'model_path': 'models/music_transformer',
                'ipc_pipe_name': 'test_plaialong_midi',
                'instruments': ['bass', 'drums', 'pad'],
                'generation_length_bars': 8
            },
            'cloud_manager': {
                'mock_generation_time': 0.1,  # Fast for testing
                'timeout_seconds': 5,
                'stem_directory': str(self.temp_dir / 'cloud_stems')
            }
        }
        
        # Initialize shared memory
        self.ssm = SessionStateManager(self.config['audio']['shared_memory_name'])
        self.ssm.init_shared_state(create=True)
        
        # Initialize services
        self.local_generator = LocalGenerator(self.ssm, self.config)
        self.cloud_manager = CloudManager(self.ssm, self.config)
    
    def tearDown(self):
        """Clean up after tests."""
        self.local_generator.stop()
        self.cloud_manager.stop()
        self.ssm.close()
        # Clean up temp directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_parse_instruction_returns_valid_structure(self):
        """Test that parsing returns a valid structure with expected fields."""
        instruction = "generate a happy upbeat track in C major"
        params = parse_text_instruction(instruction)
        
        # Verify structure exists
        self.assertIn('key', params)
        self.assertIn('mood', params)
        self.assertIn('tempo', params)
        self.assertIn('instruction', params)
        
        # Verify types and reasonable ranges
        self.assertIsInstance(params['key'], int)
        self.assertGreaterEqual(params['key'], 0)
        self.assertLess(params['key'], 12)  # 12 keys (C through B)
        
        self.assertIsInstance(params['mood'], str)
        self.assertGreater(len(params['mood']), 0)
        
        self.assertIsInstance(params['tempo'], int)
        self.assertGreater(params['tempo'], 0)
        self.assertLess(params['tempo'], 300)  # Reasonable BPM range
    
    def test_local_generator_generates_midi_from_text(self):
        """Test that LocalGenerator can generate MIDI from text instruction."""
        instruction = "happy upbeat track in C major"
        params = parse_text_instruction(instruction)
        
        # Create context from parsed parameters
        context = {
            'key': float(params['key']),
            'tempo': float(params['tempo'])
        }
        
        # Generate MIDI for each instrument
        for instrument in self.local_generator.instruments:
            midi = self.local_generator.generate_midi_pattern(context, instrument)
            
            # Verify MIDI was generated
            self.assertIsNotNone(midi, f"Failed to generate MIDI for {instrument}")
            self.assertGreater(len(midi.tracks), 0, f"MIDI has no tracks for {instrument}")
            
            # Save MIDI file for verification
            midi_file = self.output_dir / f"test_{instrument}_from_text.mid"
            midi.save(str(midi_file))
            
            # Verify file exists
            self.assertTrue(midi_file.exists(), f"MIDI file not created for {instrument}")
            self.assertGreater(midi_file.stat().st_size, 0, f"MIDI file is empty for {instrument}")
    
    def test_cloud_manager_generates_audio_from_text(self):
        """Test that CloudManager can generate audio stem from text instruction."""
        instruction = "energetic fast track in E major"
        params = parse_text_instruction(instruction)
        
        # Create context from parsed parameters
        context = {
            'key': float(params['key']),
            'tempo': float(params['tempo']),
            'loop_length_bars': 8,
            'vibe': params['mood'],
            'harmonic_context': [],
            'rhythmic_context': []
        }
        
        # Generate audio stem using CloudManager
        stem_path = self.cloud_manager.mock_generate_stem(context)
        
        # Verify stem was generated
        self.assertIsNotNone(stem_path, "Failed to generate cloud stem")
        self.assertTrue(os.path.exists(stem_path), "Cloud stem file does not exist")
        
        # Verify it's a valid audio file
        try:
            audio, sample_rate = sf.read(stem_path)
            self.assertGreater(len(audio), 0, "Audio file is empty")
            self.assertEqual(sample_rate, self.sample_rate, "Sample rate mismatch")
            self.assertTrue(np.all(np.abs(audio) <= 1.0), "Audio has clipping")
        except Exception as e:
            self.fail(f"Failed to read generated audio file: {e}")
        
        # Copy to output directory for inspection
        output_file = self.output_dir / "test_cloud_stem_from_text.wav"
        shutil.copy(stem_path, output_file)
        self.assertTrue(output_file.exists())
    
    def test_full_text_to_track_pipeline(self):
        """Test complete pipeline: text -> parse -> generate MIDI + audio."""
        instruction = "calm peaceful music in F major"
        params = parse_text_instruction(instruction)
        
        # Create context
        context = {
            'key': float(params['key']),
            'tempo': float(params['tempo']),
            'loop_length_bars': 8,
            'vibe': params['mood'],
            'harmonic_context': [],
            'rhythmic_context': []
        }
        
        # Generate MIDI patterns using LocalGenerator
        midi_files = []
        for instrument in self.local_generator.instruments:
            midi = self.local_generator.generate_midi_pattern(context, instrument)
            self.assertIsNotNone(midi)
            
            # Save MIDI
            midi_file = self.output_dir / f"test_pipeline_{instrument}.mid"
            midi.save(str(midi_file))
            midi_files.append(midi_file)
        
        # Generate audio stem using CloudManager
        stem_path = self.cloud_manager.mock_generate_stem(context)
        self.assertIsNotNone(stem_path)
        
        # Copy stem to output directory
        output_stem = self.output_dir / "test_pipeline_cloud_stem.wav"
        shutil.copy(stem_path, output_stem)
        
        # Verify all files were created
        for midi_file in midi_files:
            self.assertTrue(midi_file.exists())
        
        self.assertTrue(output_stem.exists())
        
        # Verify audio can be loaded
        audio, sr = sf.read(output_stem)
        self.assertGreater(len(audio), 0)
        self.assertEqual(sr, self.sample_rate)
    
    def test_different_instructions_produce_different_outputs(self):
        """Test that different instructions produce different MIDI/audio."""
        instruction1 = "happy upbeat track"
        instruction2 = "sad slow song"
        
        params1 = parse_text_instruction(instruction1)
        params2 = parse_text_instruction(instruction2)
        
        context1 = {
            'key': float(params1['key']),
            'tempo': float(params1['tempo']),
            'loop_length_bars': 8,
            'vibe': params1['mood'],
            'harmonic_context': [],
            'rhythmic_context': []
        }
        
        context2 = {
            'key': float(params2['key']),
            'tempo': float(params2['tempo']),
            'loop_length_bars': 8,
            'vibe': params2['mood'],
            'harmonic_context': [],
            'rhythmic_context': []
        }
        
        # Generate MIDI for both
        midi1 = self.local_generator.generate_midi_pattern(context1, 'bass')
        midi2 = self.local_generator.generate_midi_pattern(context2, 'bass')
        
        # Generate audio for both
        stem1 = self.cloud_manager.mock_generate_stem(context1)
        stem2 = self.cloud_manager.mock_generate_stem(context2)
        
        # Verify they're different
        # MIDI files should have different tempos
        # Extract tempo from MIDI (simplified check)
        self.assertIsNotNone(midi1)
        self.assertIsNotNone(midi2)
        
        # Audio files should be different
        audio1, _ = sf.read(stem1)
        audio2, _ = sf.read(stem2)
        
        # Check they're not identical
        self.assertFalse(np.array_equal(audio1, audio2), "Different instructions produced identical audio")
        
        # Check RMS is different (different tempos should produce different energy)
        rms1 = np.sqrt(np.mean(audio1 ** 2))
        rms2 = np.sqrt(np.mean(audio2 ** 2))
        self.assertNotAlmostEqual(rms1, rms2, places=3, msg="Audio characteristics are too similar")


if __name__ == '__main__':
    unittest.main()
