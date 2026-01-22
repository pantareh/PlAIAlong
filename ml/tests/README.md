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
```

### Using unittest:
```bash
cd ml/tests
python test_session_state.py
python test_input_listener.py
```

**Note:** Tests must be run from within the activated virtual environment.
