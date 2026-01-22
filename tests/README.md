# PlAIAlong Tests

## ML Layer Tests

Run ML layer tests:
```bash
cd tests/ml
python -m pytest test_session_state.py test_input_listener.py
```

Or using unittest:
```bash
python test_session_state.py
python test_input_listener.py
```

## Audio Engine Tests

Build and run audio engine tests:
```bash
cd tests/audio_engine
mkdir build && cd build
cmake ..
make
./test_shared_memory
```

Note: Audio engine tests require Google Test framework.
