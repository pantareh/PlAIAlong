#!/usr/bin/env python3
"""
Command-line utility to generate MIDI and audio tracks from text prompts.

Usage:
    python src/generate_track.py "<prompt>" [options]
    
Options:
    --midi-only          Generate only MIDI files (no audio)
    --audio-only         Generate only audio file (no MIDI)
    --instrument <name>  Generate MIDI for specific instrument only (bass, drums, pad)
    --output-dir <path>   Output directory (default: current directory)
    --format <ext>      Audio format: wav, flac, ogg (default: wav)
    
Examples:
    # Generate both MIDI and audio
    python src/generate_track.py "happy upbeat track in C major"
    
    # Generate only MIDI files
    python src/generate_track.py "sad slow song" --midi-only
    
    # Generate only audio
    python src/generate_track.py "energetic fast track" --audio-only
    
    # Generate MIDI for specific instrument
    python src/generate_track.py "calm peaceful music" --instrument bass
    
    # Specify output directory
    python src/generate_track.py "jazz track in E minor" --output-dir ./output
"""
import sys
import os
import argparse
import yaml
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import parse_text_instruction
from src.local_generator import LocalGenerator
from src.cloud_manager import CloudManager
from src.session_state import SessionStateManager


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def sanitize_filename(text: str, max_length: int = 50) -> str:
    """Sanitize text for use in filename."""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        text = text.replace(char, '_')
    # Remove extra spaces and limit length
    text = '_'.join(text.split())
    if len(text) > max_length:
        text = text[:max_length]
    return text


def generate_tracks(prompt: str, config: dict, output_dir: Path, 
                   midi_only: bool = False, audio_only: bool = False,
                   instrument: str = None, audio_format: str = 'wav'):
    """Generate MIDI and/or audio tracks from text prompt."""
    
    # Parse instruction
    print(f"Parsing instruction: '{prompt}'")
    params = parse_text_instruction(prompt)
    print(f"  Key: {params['key']}, Mood: {params['mood']}, Tempo: {params['tempo']} BPM")
    
    # Create context
    context = {
        'key': float(params['key']),
        'tempo': float(params['tempo']),
        'loop_length_bars': config['session']['default_loop_length_bars'],
        'vibe': params['mood'],
        'harmonic_context': [],
        'rhythmic_context': []
    }
    
    # Initialize services
    ssm = SessionStateManager(config['audio']['shared_memory_name'])
    ssm.init_shared_state(create=True)
    
    local_generator = LocalGenerator(ssm, config)
    cloud_manager = CloudManager(ssm, config)
    
    try:
        generated_files = []
        
        # Generate MIDI files
        if not audio_only:
            instruments = [instrument] if instrument else local_generator.instruments
            
            print(f"\nGenerating MIDI files for instruments: {instruments}")
            for inst in instruments:
                midi = local_generator.generate_midi_pattern(context, inst)
                if midi:
                    # Create filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    prompt_safe = sanitize_filename(prompt)
                    filename = f"{prompt_safe}_{inst}_{timestamp}.mid"
                    filepath = output_dir / filename
                    
                    # Save MIDI
                    midi.save(str(filepath))
                    print(f"  ✓ Saved: {filepath}")
                    generated_files.append(filepath)
                else:
                    print(f"  ✗ Failed to generate MIDI for {inst}")
        
        # Generate audio file
        if not midi_only:
            print(f"\nGenerating audio stem...")
            stem_path = cloud_manager.mock_generate_stem(context)
            
            if stem_path and os.path.exists(stem_path):
                # Create filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                prompt_safe = sanitize_filename(prompt)
                filename = f"{prompt_safe}_audio_{timestamp}.{audio_format}"
                filepath = output_dir / filename
                
                # Copy and optionally convert format
                import shutil
                import soundfile as sf
                import numpy as np
                
                # Read original audio
                audio, sample_rate = sf.read(stem_path)
                
                # Save in requested format
                sf.write(str(filepath), audio, sample_rate, format=audio_format)
                print(f"  ✓ Saved: {filepath}")
                generated_files.append(filepath)
            else:
                print(f"  ✗ Failed to generate audio stem")
        
        print(f"\n✓ Generated {len(generated_files)} file(s)")
        return generated_files
        
    finally:
        # Cleanup
        local_generator.stop()
        cloud_manager.stop()
        ssm.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate MIDI and audio tracks from text prompts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('prompt', type=str, help='Text prompt describing the track to generate')
    parser.add_argument('--midi-only', action='store_true', 
                       help='Generate only MIDI files (no audio)')
    parser.add_argument('--audio-only', action='store_true',
                       help='Generate only audio file (no MIDI)')
    parser.add_argument('--instrument', type=str, choices=['bass', 'drums', 'pad'],
                       help='Generate MIDI for specific instrument only')
    parser.add_argument('--output-dir', type=str, default='.',
                       help='Output directory (default: current directory)')
    parser.add_argument('--format', type=str, choices=['wav', 'flac', 'ogg'], default='wav',
                       help='Audio format (default: wav)')
    parser.add_argument('--config', type=str,
                       help='Path to config.yaml (default: ml/config/config.yaml)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.midi_only and args.audio_only:
        print("Error: Cannot specify both --midi-only and --audio-only")
        return 1
    
    # Find config file
    if args.config:
        config_path = Path(args.config)
    else:
        script_dir = Path(__file__).parent
        config_path = script_dir.parent / "config" / "config.yaml"
    
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        return 1
    
    # Load config
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"Error loading config: {e}")
        return 1
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate tracks
    try:
        files = generate_tracks(
            args.prompt,
            config,
            output_dir,
            midi_only=args.midi_only,
            audio_only=args.audio_only,
            instrument=args.instrument,
            audio_format=args.format
        )
        
        if files:
            print(f"\nAll files saved to: {output_dir.absolute()}")
            return 0
        else:
            print("\nNo files were generated")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
