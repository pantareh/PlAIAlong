# Audio Engine Tests

Build and run audio engine tests:

```bash
cd audio_engine/tests
mkdir build && cd build
cmake ..
cmake --build . --config Release

# Run tests
./test_shared_memory  # Linux/macOS
# or
.\test_shared_memory.exe  # Windows
```

**Note:** Google Test is automatically downloaded and built by CMake using FetchContent. No manual installation required!

The first build will download Google Test from GitHub (requires internet connection). Subsequent builds will use the cached version.
