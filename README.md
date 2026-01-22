# PlAIAlong - Live AI Band MVP

A hybrid Python + C++ real-time AI music collaboration system that listens to a performer and dynamically generates complementary instrumentation with tight synchronization.

## Architecture

- **ML Layer** (`ml/`): ML/AI components (MusicTransformer, audio analysis, voice commands, cloud manager)
- **Audio Engine** (`audio_engine/`): Real-time audio I/O (ASIO), synchronization (DTW), and mixing

## Requirements

### ML Layer (Python)
- **Python 3.10 or 3.11** (recommended)
  - PyTorch requires Python 3.10+ and has full binary support for 3.10 and 3.11
  - Python 3.12 and 3.13 may have compatibility issues with PyTorch
- See `ml/requirements.txt`

### Audio Engine (C++)
- C++17 compatible compiler
- CMake 3.15+
- ASIO SDK (for Windows) or PortAudio

## Building

### ML Layer Setup
```bash
cd ml

# Verify Python version (should be 3.10 or 3.11)
python --version

# Work in virtual environment
# Install dependencies
pip install -r requirements.txt
```

### Audio Engine Build
```bash
cd audio_engine
mkdir build && cd build
cmake ..
make  # or ninja on Windows with Visual Studio
```

## Configuration

Edit `ml/config/config.yaml` to configure:
- Audio device settings
- Input channel routing (guitar on channel 1, voice on channel 2)
- Session parameters
- Model paths

## Usage

```bash
# Start the application
python ml/src/main.py
```

## Testing

The system supports multi-channel audio input:
- **Channel 1**: Guitar/Instrument input (for harmonic/rhythmic analysis)
- **Channel 2**: Voice input (for voice commands)

Connect your audio interface and configure the channels in `config.yaml`.
