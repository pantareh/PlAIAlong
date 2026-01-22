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
- **C++17 compatible compiler** - Choose one:
  - **Visual Studio 2026** (recommended for Windows) - Download from [visualstudio.microsoft.com](https://visualstudio.microsoft.com/)
    - Install "Desktop development with C++" workload
  - **Visual Studio 2019/2022** - Also supported
  - **MinGW-w64** - Download from [mingw-w64.org](https://www.mingw-w64.org/) or use MSYS2
- **CMake 3.15+** - Download from [cmake.org/download](https://cmake.org/download/)
  - Windows: Use the Windows x64 Installer (.msi) for easiest installation
  - Alternative: Install via `winget install Kitware.CMake` or Chocolatey
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

**Windows (Visual Studio):**
```bash
cd audio_engine
mkdir build && cd build

# Option 1: Use Visual Studio 2026 generator (recommended)
cmake .. -G "Visual Studio 18 2026" -A x64
cmake --build . --config Release

# Option 2: Use Visual Studio Developer Command Prompt
# Open "x64 Native Tools Command Prompt for VS 2026" from Start Menu, then:
cmake ..
cmake --build . --config Release

# If you have a different Visual Studio version, try:
# cmake .. -G "Visual Studio 17 2022" -A x64
# cmake .. -G "Visual Studio 16 2019" -A x64
```

**Windows (MinGW) - Alternative if Visual Studio not available:**
```bash
cd audio_engine
mkdir build && cd build
cmake .. -G "MinGW Makefiles"
mingw32-make
```

**Windows (Ninja) - Fast alternative:**
```bash
# Install Ninja: winget install Ninja-build.Ninja
cd audio_engine
mkdir build && cd build
cmake .. -G "Ninja"
ninja
```

**Windows (NMake) - If you have Visual Studio Build Tools:**
```bash
cd audio_engine
mkdir build && cd build
cmake .. -G "NMake Makefiles"
nmake
```

**macOS/Linux:**
```bash
cd audio_engine
mkdir build && cd build
cmake ..
make
```

**Troubleshooting:**
- **"Visual Studio could not find any instance"**: Install Visual Studio 2026 (or 2019/2022) with "Desktop development with C++" workload, or use MinGW/Ninja generators instead
- **"CMAKE_C_COMPILER not set"**: Ensure your compiler is installed and in PATH, or specify generator with `-G` option
- **"No generator specified"**: Run `cmake -G` to see available generators on your system

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

Tests are co-located with their respective components:

### ML Layer Tests
See `ml/tests/README.md` for details:
```bash
cd ml/tests
python -m pytest test_session_state.py test_input_listener.py
```

### Audio Engine Tests
See `audio_engine/tests/README.md` for details:
```bash
cd audio_engine/tests
mkdir build && cd build
cmake ..
cmake --build . --config Release
```

## Audio Input Configuration

The system supports multi-channel audio input:
- **Channel 1**: Guitar/Instrument input (for harmonic/rhythmic analysis)
- **Channel 2**: Voice input (for voice commands)

Connect your audio interface and configure the channels in `ml/config/config.yaml`.
