# ML Layer Utilities

This directory contains utility scripts and functions for the PlAIAlong ML layer.

## Track Generator (`generate_track.py`)

A command-line utility to generate MIDI and audio tracks from text prompts.

### Usage

```bash
python src/generate_track.py "<prompt>" [options]
```

### Options

- `--midi-only` - Generate only MIDI files (no audio)
- `--audio-only` - Generate only audio file (no MIDI)
- `--instrument <name>` - Generate MIDI for specific instrument only: `bass`, `drums`, or `pad`
- `--output-dir <path>` - Output directory (default: current directory)
- `--format <ext>` - Audio format: `wav`, `flac`, or `ogg` (default: `wav`)
- `--config <path>` - Path to config.yaml (default: `ml/config/config.yaml`)

### Examples

#### Generate Both MIDI and Audio
```bash
# Generate MIDI files for all instruments and audio stem
python src/generate_track.py "happy upbeat track in C major"

# Output:
# - happy_upbeat_track_in_C_major_bass_20240101_120000.mid
# - happy_upbeat_track_in_C_major_drums_20240101_120000.mid
# - happy_upbeat_track_in_C_major_pad_20240101_120000.mid
# - happy_upbeat_track_in_C_major_audio_20240101_120000.wav
```

#### Generate Only MIDI Files
```bash
# Generate MIDI files only
python src/generate_track.py "sad slow song" --midi-only
```

#### Generate Only Audio
```bash
# Generate audio stem only
python src/generate_track.py "energetic fast track" --audio-only
```

#### Generate MIDI for Specific Instrument
```bash
# Generate only bass MIDI
python src/generate_track.py "calm peaceful music" --instrument bass
```

#### Specify Output Directory
```bash
# Save files to custom directory
python src/generate_track.py "jazz track in E minor" --output-dir ./output
```

#### Change Audio Format
```bash
# Generate audio in FLAC format
python src/generate_track.py "rock track" --audio-only --format flac
```

### How It Works

1. **Parses the text prompt** using an LLM to extract:
   - Key (musical key: C, D, E, etc.)
   - Mood (happy, sad, energetic, etc.)
   - Tempo (BPM)

2. **Generates MIDI patterns** using `LocalGenerator`:
   - Creates MIDI files for each instrument (bass, drums, pad)
   - Patterns are generated based on the parsed musical parameters

3. **Generates audio stem** using `CloudManager`:
   - Creates a WAV/FLAC/OGG audio file
   - Audio is synthesized from the musical context

### Notes

- Generated files include timestamps to prevent overwrites
- Filenames are sanitized from the prompt text
- By default, generates MIDI for all instruments and audio stem
- Requires proper configuration in `ml/config/config.yaml`

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
