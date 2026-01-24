# ML Layer Utilities

This directory contains utility scripts and functions for the PlAIAlong ML layer.

## MIDI File Parser (`parse_midi.py`)

A command-line utility to parse MIDI files into human-readable formats.

### Usage

```bash
python src/parse_midi.py <midi_file> [options]
```

### Options

- `--tabs` - Output in tablature format (6 lines) instead of table format
- `--instrument <type>` - Specify instrument type for tab format:
  - `guitar` - Guitar tablature (6 strings: E, B, G, D, A, E)
  - `drums` - Drum tablature (6 lines: Kick, Snare, Hi-Hat, Crash, Ride, Toms)
  - `keyboard` - Keyboard/piano tablature (6 octave lines: C5 to C0)
  - `auto` - Auto-detect instrument type (default)

### Examples

#### Standard Table Format
```bash
# Parse MIDI file to tab-separated table
python src/parse_midi.py tests/generated_tracks/test_bass_from_text.mid
```

Output shows:
- Time in seconds
- Track name
- Event type (NoteOn, NoteOff, Tempo, etc.)
- Note name and MIDI number
- Velocity, Channel, Duration
- Additional info

#### Tablature Format (Auto-detect)
```bash
# Parse with tab format, auto-detect instrument
python src/parse_midi.py tests/generated_tracks/test_bass_from_text.mid --tabs
```

#### Tablature Format (Specify Instrument)
```bash
# Guitar tabs
python src/parse_midi.py test.mid --tabs --instrument guitar

# Drum tabs
python src/parse_midi.py test.mid --tabs --instrument drums

# Keyboard tabs
python src/parse_midi.py test.mid --tabs --instrument keyboard
```

### Tab Format Details

#### Guitar Tablature
- 6 strings: E (high), B, G, D, A, E (low)
- Shows fret numbers on each string
- Example:
  ```
  E |----3-5-7---
  B |------------
  G |------------
  D |------------
  A |------------
  E |------------
  ```

#### Drum Tablature
- 6 lines: Kick, Snare, Hi-Hat, Crash, Ride, Toms
- Symbols: K (Kick), S (Snare), H (Hi-Hat), C (Crash), R (Ride), T/M/L (Toms)
- Example:
  ```
  Kick    |K---K---K---K---
  Snare   |----S-------S---
  Hi-Hat  |H-H-H-H-H-H-H-H
  ```

#### Keyboard Tablature
- 6 octave lines: C5 down to C0
- Shows note names (C, C#, D, etc.) in each octave
- Example:
  ```
  C5 |----C----E----
  C4 |C---E---G---
  C3 |------------
  ```

### Python API

You can also use the parsing functions directly in Python:

```python
from src.utils import parse_midi_file, parse_midi_to_tabs

# Table format
table_output = parse_midi_file("test.mid")
print(table_output)

# Tab format
tab_output = parse_midi_to_tabs("test.mid", instrument_type="guitar")
print(tab_output)
```

### Notes

- Tab format uses 16th-note quantization for readability
- Auto-detection checks for:
  - Channel 9 → Drums
  - Note range 40-88 → Guitar
  - Otherwise → Keyboard
- All times are in seconds
- Note names use standard notation (C, C#, D, etc.)
