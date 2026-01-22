# PlAIAlong Tests

## Python Tests

Run Python tests:
```bash
cd tests/python
python -m pytest test_session_state.py test_input_listener.py
```

Or using unittest:
```bash
python test_session_state.py
python test_input_listener.py
```

## C++ Tests

Build and run C++ tests:
```bash
cd tests/cpp
mkdir build && cd build
cmake ..
make
./test_shared_memory
```

Note: C++ tests require Google Test framework.
