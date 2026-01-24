# ML Layer Tests

## Setup

First, ensure the virtual environment is activated and dependencies are installed:

```bash
cd ml

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Windows (CMD):
.\venv\Scripts\activate.bat
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements.dev.txt  # Install development dependencies (pytest, etc.)
```

## Running Tests

### Using pytest (recommended):
```bash
cd ml/tests
pytest -v
# Or run specific test file:
pytest test_session_state.py -v
pytest test_input_listener.py -v
pytest test_text_to_track.py -v
```

### Using unittest:
```bash
cd ml/tests
python test_session_state.py
python test_input_listener.py
python test_text_to_track.py
```

## Test Descriptions

### test_session_state
Tests shared memory functionality between Python and C++ layers.

### test_input_listener
Tests audio input processing and voice command detection.

### test_text_to_track
Tests text-to-track generation:
- Parses text instructions (e.g., "happy upbeat track in C major")
- Generates audio tracks based on mood, key, and tempo
- **Outputs WAV files**: Generated tracks are saved in `ml/tests/generated_tracks/`
  - `test_happy_track.wav`
  - `test_sad_track.wav`
  - `test_energetic_track.wav`
  - `test_calm_track.wav`

**Note:** Tests must be run from within the activated virtual environment.
