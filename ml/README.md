# ML Layer (ml/)

This directory contains the machine learning and high-level logic components for PlAIAlong.

## Components

- `src/`: Core logic and service implementations.
- `config/`: Configuration files (YAML).
- `models/`: Directory for pre-trained model checkpoints (ignored by git).
- `tests/`: Unit and integration tests.

## Installation

### 1. Prerequisites
- Python 3.10 or 3.11 (3.11 recommended for Windows).
- (Optional) NVIDIA GPU with CUDA for faster generation.

### 2. Setup Virtual Environment
```powershell
# From the ml/ directory
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

#### Standard Installation (CPU)
```powershell
pip install -r requirements.txt
```

#### GPU Installation (NVIDIA CUDA - Windows)
**Note:** This section is only for users with **NVIDIA** GPUs (RTX/GTX series). 

To use your NVIDIA GPU for faster AI music generation...

...

4.  **Verify CUDA is available**:
    ```powershell
    python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
    ```

#### Hardware Acceleration for Intel/AMD Users
If you have an **Intel Core Ultra** (like the 258V) or an **AMD Ryzen AI** processor:
*   **Standard Installation**: The CPU is highly optimized and will work great by default.
*   **Intel Arc/NPU**: To use your Intel GPU or NPU, you must use the [Intel Extension for PyTorch (IPEX)](https://intel.github.io/intel-extension-for-pytorch/index.html#installation). Use the `xpu` device instead of `cuda` in the code.

## CUDA Setup on Windows

If you haven't installed CUDA before, follow these steps:

1.  **Install NVIDIA Drivers**: Ensure you have the latest drivers for your GPU from [nvidia.com/drivers](https://www.nvidia.com/drivers).
2.  **Install CUDA Toolkit**:
    - Download and install the [CUDA Toolkit 12.1](https://developer.nvidia.com/cuda-12-1-0-download-archive) (or the latest version compatible with your GPU).
    - During installation, choose "Express" or ensure "Visual Studio Integration" is checked if you plan to do C++ GPU development.
3.  **Restart your computer**: This ensures all environment variables and paths are correctly updated.

## Model Setup

See [models/README.md](models/README.md) for instructions on downloading pre-trained model checkpoints.

## Running Tests

```powershell
# Install dev dependencies
pip install -r requirements.dev.txt

# Run all tests
pytest
```
