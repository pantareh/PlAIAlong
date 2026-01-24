# Audio Engine Tests

Build and run audio engine tests:

```bash
cd audio_engine/tests
mkdir build && cd build
cmake ..
cmake --build . --config Release

# Run all tests
ctest --output-on-failure

# Or run individual tests
./test_shared_memory  # Linux/macOS
./test_audio_generation  # Linux/macOS
# or
.\test_shared_memory.exe  # Windows
.\test_audio_generation.exe  # Windows
```

## Test Descriptions

### test_shared_memory
Tests shared memory functionality between Python and C++ layers.

### test_audio_generation
Tests audio generation and streaming:
- Generates 8-bit square wave audio
- Generates sine wave audio
- Simulates audio streaming in chunks
- **Outputs WAV files**: `test_8bit_square.wav`, `test_sine.wav`, `test_streamed_8bit.wav`

The audio generation test creates actual WAV files that you can play to verify the audio output.

**Note:** Google Test is automatically downloaded and built by CMake using FetchContent. No manual installation required!

The first build will download Google Test from GitHub (requires internet connection). Subsequent builds will use the cached version.
