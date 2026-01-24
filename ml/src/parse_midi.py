#!/usr/bin/env python3
"""
Command-line utility to parse MIDI files into human-readable format.

Usage:
    python src/parse_midi.py <midi_file> [--tabs] [--instrument <type>]
    
Options:
    --tabs              Output in tablature format (6 lines)
    --instrument <type> Instrument type: "guitar", "drums", "keyboard", or "auto" (default: auto)
    
Examples:
    python src/parse_midi.py test.mid
    python src/parse_midi.py test.mid --tabs
    python src/parse_midi.py test.mid --tabs --instrument guitar
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import parse_midi_file, parse_midi_to_tabs


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    midi_path = sys.argv[1]
    use_tabs = "--tabs" in sys.argv
    instrument_type = "auto"
    
    # Parse instrument type if provided
    if "--instrument" in sys.argv:
        idx = sys.argv.index("--instrument")
        if idx + 1 < len(sys.argv):
            instrument_type = sys.argv[idx + 1]
    
    if not os.path.exists(midi_path):
        print(f"Error: MIDI file not found: {midi_path}")
        sys.exit(1)
    
    if not midi_path.lower().endswith(('.mid', '.midi')):
        print(f"Warning: File doesn't have .mid or .midi extension: {midi_path}")
    
    if use_tabs:
        print(parse_midi_to_tabs(midi_path, instrument_type))
    else:
        print(parse_midi_file(midi_path))


if __name__ == '__main__':
    main()
