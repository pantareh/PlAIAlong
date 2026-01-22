# PlAIAlong - Live AI Band MVP

A hybrid Python + C++ real-time AI music collaboration system that listens to a performer and dynamically generates complementary instrumentation with tight synchronization.

## Architecture

- **Python Layer**: ML/AI components (MusicTransformer, audio analysis, voice commands, cloud manager)
- **C++ Layer**: Real-time audio I/O (ASIO), synchronization (DTW), and mixing

## Requirements

### Python
- Python 3.10+
- See `python/requirements.txt`

### C++
- C++17 compatible compiler
- CMake 3.15+
- ASIO SDK (for Windows) or PortAudio

## Building

### Python Setup
```bash
cd python
pip install -r requirements.txt
```

### C++ Build
```bash
cd cpp
mkdir build && cd build
cmake ..
make  # or ninja on Windows with Visual Studio
```

## Configuration

Edit `python/config/config.yaml` to configure:
- Audio device settings
- Input channel routing (guitar on channel 1, voice on channel 2)
- Session parameters
- Model paths

## Usage

```bash
# Start the application
python python/src/main.py
```

## Testing

The system supports multi-channel audio input:
- **Channel 1**: Guitar/Instrument input (for harmonic/rhythmic analysis)
- **Channel 2**: Voice input (for voice commands)

Connect your audio interface and configure the channels in `config.yaml`.
