"""
Local Generator - Generates MIDI patterns using MusicTransformer and sends to C++.

Transformer Integration:
    This module uses transformer models (Orpheus Music Transformer, etc.) for MIDI generation.
    A transformer model MUST be configured and loaded successfully for MIDI generation to work.
    There is no fallback - transformer model is required.
    
    To enable transformer generation:
    1. Download model checkpoint (see ml/models/README.md)
    2. Update config.yaml with model path
    3. Implement token-to-MIDI conversion logic for your specific model
    
    Current Status:
    - Model loading: Implemented (supports Hugging Face and local checkpoints)
    - Token generation: Implemented (for Hugging Face models)
    - Token-to-MIDI conversion: Requires model-specific implementation
    - Rule-based fallback: Removed - transformer model required for generation
"""
import torch
import mido
import numpy as np
import time
import threading
import os
import sys
import struct
from pathlib import Path
from typing import Optional, Dict, Any, List
from .session_state import SessionStateManager


class LocalGenerator:
    """Generates complementary MIDI patterns using MusicTransformer."""
    
    def __init__(self, ssm: SessionStateManager, config: Dict[str, Any]):
        self.ssm = ssm
        self.config = config
        self.running = False
        self.thread = None
        
        # Model parameters
        self.model_path = config['local_generator']['model_path']
        self.instruments = config['local_generator']['instruments']
        self.generation_length_bars = config['local_generator']['generation_length_bars']
        self.ipc_pipe_name = config['local_generator']['ipc_pipe_name']
        
        # Model state
        self.model = None
        self.model_type = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Generation state
        self.current_midi = None
        self.last_generation_time = 0
        self.generation_interval = 8.0  # Generate every 8 bars (at loop boundary)
        
        # IPC pipe
        self.pipe = None
        
        # Initialize model (lazy loading)
        self._init_model()
        self._init_ipc()
    
    def _init_model(self):
        """Initialize MusicTransformer model."""
        try:
            model_path_str = str(self.model_path)
            
            # Check if this is a Hugging Face model ID (contains "/" and doesn't look like a file path)
            is_hf_model_id = (
                "/" in model_path_str and 
                not model_path_str.endswith((".pth", ".pt", ".bin", ".ckpt", ".safetensors")) and
                not model_path_str.startswith((".", "/", "\\")) and
                "\\" not in model_path_str  # Windows path separator
            )
            
            if is_hf_model_id:
                # This is a Hugging Face model ID, pass it directly as string
                print(f"Detected Hugging Face model ID: {model_path_str}")
                print(f"Loading MusicTransformer model from Hugging Face: {model_path_str}...")
                # Pass as string, not Path object
                model_path = model_path_str
            else:
                # This is a file path, resolve it
                model_path = Path(self.model_path)
                
                # Resolve relative paths
                if not model_path.is_absolute():
                    # Try relative to config directory, then to ml/ directory
                    script_dir = Path(__file__).parent.parent
                    possible_paths = [
                        script_dir / model_path,
                        script_dir / "models" / model_path.name,
                        script_dir.parent / "models" / model_path.name,
                    ]
                    for path in possible_paths:
                        if path.exists():
                            model_path = path
                            break
                
                if not model_path.exists():
                    print(f"Warning: Model checkpoint not found at {model_path}")
                    print("MIDI generation will not be available. Download model checkpoint to enable transformer generation.")
                    self.model = None
                    self.model_type = None
                    return
                
                print(f"Loading MusicTransformer model from {model_path}...")
            
            # Try to detect model type and load accordingly
            self.model = self._load_transformer_model(model_path)
            
            if self.model is None:
                print("Warning: Could not load transformer model. MIDI generation will not be available.")
            else:
                print("MusicTransformer model loaded successfully")
                
        except Exception as e:
            print(f"Warning: Could not load MusicTransformer model: {e}")
            print("MIDI generation will not be available until a valid model is configured")
            self.model = None
            self.model_type = None
    
    def _load_transformer_model(self, model_path) -> Optional[Any]:
        """Load transformer model, trying different implementations."""
        # Handle both Path objects and strings (for Hugging Face model IDs)
        if isinstance(model_path, str):
            # This is a Hugging Face model ID
            return self._load_orpheus_model(model_path)
        
        # Try Orpheus Music Transformer (Hugging Face compatible)
        try:
            return self._load_orpheus_model(model_path)
        except Exception as e:
            print(f"  Orpheus model loading failed: {e}")
        
        # Try generic MusicTransformer-Pytorch
        try:
            return self._load_generic_musictransformer(model_path)
        except Exception as e:
            print(f"  Generic MusicTransformer loading failed: {e}")
        
        return None
    
    def _load_orpheus_model(self, model_path) -> Optional[Any]:
        """Load Orpheus Music Transformer model."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Handle both Path objects and strings (for Hugging Face model IDs)
            if isinstance(model_path, str):
                model_path_str = model_path
                is_hf_model_id = True
            else:
                model_path_str = str(model_path)
                # Check if path is a Hugging Face model ID
                is_hf_model_id = (
                    "/" in model_path_str and 
                    not model_path_str.endswith((".pth", ".pt", ".bin", ".ckpt", ".safetensors")) and
                    not model_path_str.startswith((".", "/", "\\")) and
                    "\\" not in model_path_str and  # Not a Windows path
                    not Path(model_path_str).exists()  # Not a local file
                ) or "asigalov61/Orpheus" in model_path_str
            
            # First try Hugging Face model
            if is_hf_model_id or (isinstance(model_path, Path) and not model_path.exists()):
                try:
                    # Use Hugging Face model ID
                    if is_hf_model_id:
                        model_id = model_path_str
                    else:
                        # Default to Orpheus if path doesn't exist
                        model_id = "asigalov61/Orpheus-Music-Transformer"
                    
                    print(f"  Loading Orpheus from Hugging Face: {model_id}")
                    try:
                        # Try with trust_remote_code in case it needs custom model code
                        model = AutoModelForCausalLM.from_pretrained(
                            model_id,
                            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                            device_map="auto" if torch.cuda.is_available() else None,
                            trust_remote_code=True
                        )
                        tokenizer = AutoTokenizer.from_pretrained(
                            model_id,
                            trust_remote_code=True
                        )
                        self.model_type = "orpheus_hf"
                        print(f"  ✓ Model type set to: {self.model_type}")
                        return {
                            'model': model,
                            'tokenizer': tokenizer,
                            'device': self.device
                        }
                    except ValueError as ve:
                        # Model not recognized by AutoModel
                        error_msg = str(ve)
                        if "Unrecognized model" in error_msg or "model_type" in error_msg:
                            print(f"  ⚠ The Orpheus model is not available in standard AutoModel format")
                            print(f"  This model may require:")
                            print(f"    1. Custom model code from the original Orpheus repository")
                            print(f"    2. Using the Gradio interface at: https://huggingface.co/spaces/{model_id}")
                            print(f"    3. Loading checkpoints directly with the original model architecture")
                            raise ValueError(f"Orpheus model requires custom code: {error_msg[:200]}")
                        else:
                            raise
                except Exception as e:
                    print(f"  Hugging Face loading failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Try loading local checkpoint (only if HF loading failed or path is a .pth file)
            if isinstance(model_path, Path) and model_path.exists() and model_path.suffix == ".pth":
                print(f"  Loading local checkpoint: {model_path}")
                checkpoint = torch.load(str(model_path), map_location=self.device)
                
                if isinstance(checkpoint, dict):
                    # Extract state dict
                    if 'model_state_dict' in checkpoint:
                        state_dict = checkpoint['model_state_dict']
                    elif 'state_dict' in checkpoint:
                        state_dict = checkpoint['state_dict']
                    else:
                        state_dict = checkpoint
                    
                    print("  Detected Orpheus checkpoint format (local)")
                    
                    # Check if this is a classifier model (not suitable for generation)
                    checkpoint_name = model_path.name.lower()
                    is_classifier = "classifier" in checkpoint_name
                    if is_classifier:
                        print("  ⚠ Warning: This appears to be a Classifier model, not a generation model")
                        print("  Classifier models are for classification, not MIDI generation")
                        print("  You need the main generation model checkpoint for MIDI generation")
                        print("  Recommended: Orpheus_Music_Transformer_Trained_Model_96332_steps_*.pth")
                    
                    # Try to load Hugging Face model architecture and load checkpoint weights
                    hf_model_loaded = False
                    try:
                        from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
                        
                        # Load base model architecture from Hugging Face
                        model_id = "asigalov61/Orpheus-Music-Transformer"
                        print(f"  Loading model architecture from: {model_id}")
                        
                        try:
                            # Try loading with AutoModelForCausalLM first
                            print(f"  Attempting to load from Hugging Face...")
                            model = AutoModelForCausalLM.from_pretrained(
                                model_id,
                                torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                                device_map="auto" if torch.cuda.is_available() else None,
                                trust_remote_code=True,  # Some models need this
                                local_files_only=False  # Allow downloading if needed
                            )
                            tokenizer = AutoTokenizer.from_pretrained(
                                model_id, 
                                trust_remote_code=True,
                                local_files_only=False
                            )
                            print(f"  ✓ Successfully loaded model architecture from Hugging Face")
                            hf_model_loaded = True
                        except Exception as hf_error:
                            # If AutoModelForCausalLM fails, the model might use a custom architecture
                            error_msg = str(hf_error)
                            error_type = type(hf_error).__name__
                            print(f"  ⚠ AutoModelForCausalLM failed: {error_type}")
                            
                            # Check for specific error types
                            if "Unrecognized model" in error_msg or "model_type" in error_msg:
                                print("  ⚠ The Orpheus model is not in standard AutoModel format")
                                print("  It requires custom model code that's not available via AutoModel")
                                print("\n  💡 Solutions:")
                                print("  1. Use local checkpoint files with the original Orpheus code")
                                print("  2. Use the Gradio interface: https://huggingface.co/spaces/asigalov61/Orpheus-Music-Transformer")
                                print("  3. Clone the Orpheus repository and use their model loading code")
                                print("  4. Use a different MusicTransformer implementation that supports AutoModel")
                            elif "does not appear to have a file named" in error_msg or "not found" in error_msg.lower():
                                print("  The Orpheus model may not be available on Hugging Face in AutoModel format")
                                print("  It may require custom model code from the original repository")
                            elif "401" in error_msg or "403" in error_msg or "unauthorized" in error_msg.lower():
                                print("  Authentication required or model access restricted")
                                print("  You may need to login to Hugging Face: huggingface-cli login")
                            else:
                                print(f"  Error details: {error_msg[:300]}...")
                            
                            # If we have a checkpoint, try to analyze it
                            if isinstance(model_path, Path) and model_path.exists():
                                print("\n  📊 Analyzing checkpoint structure...")
                                try:
                                    checkpoint_keys = list(state_dict.keys())
                                    print(f"  ✓ Checkpoint contains {len(checkpoint_keys)} parameter groups")
                                    
                                    # Analyze architecture from key names
                                    has_token_emb = any('token_emb' in k for k in checkpoint_keys)
                                    has_attn_layers = any('attn_layers' in k for k in checkpoint_keys)
                                    has_ff_layers = any('ff' in k or 'feedforward' in k for k in checkpoint_keys)
                                    
                                    # Count layers
                                    layer_indices = set()
                                    for key in checkpoint_keys:
                                        if 'layers.' in key:
                                            # Extract layer index (e.g., "layers.0" -> 0)
                                            parts = key.split('layers.')
                                            if len(parts) > 1:
                                                layer_part = parts[1].split('.')[0]
                                                try:
                                                    layer_indices.add(int(layer_part))
                                                except:
                                                    pass
                                    
                                    num_layers = len(layer_indices) if layer_indices else "unknown"
                                    
                                    print(f"  Architecture components detected:")
                                    print(f"    - Token embeddings: {'✓' if has_token_emb else '✗'}")
                                    print(f"    - Attention layers: {'✓' if has_attn_layers else '✗'} ({num_layers} layers)")
                                    print(f"    - Feedforward layers: {'✓' if has_ff_layers else '✗'}")
                                    
                                    print(f"\n  Sample parameter keys (first 10):")
                                    for i, key in enumerate(checkpoint_keys[:10], 1):
                                        # Get shape info if available
                                        shape_info = ""
                                        try:
                                            if hasattr(state_dict[key], 'shape'):
                                                shape_info = f" (shape: {list(state_dict[key].shape)})"
                                        except:
                                            pass
                                        print(f"    {i}. {key}{shape_info}")
                                    
                                    print(f"\n  ⚠ This checkpoint uses a custom Orpheus architecture")
                                    print(f"  The model structure (net.token_emb, net.attn_layers, etc.)")
                                    print(f"  is not compatible with Hugging Face's AutoModel interface.")
                                    print(f"  To use this checkpoint, you need:")
                                    print(f"    1. The original Orpheus model class definition")
                                    print(f"    2. The model initialization code")
                                    print(f"    3. The tokenizer/encoder for this specific architecture")
                                    print(f"\n  💡 Recommendation: Integrate the original Orpheus repository code")
                                    print(f"     to use this checkpoint, or use an alternative MusicTransformer implementation.")
                                except Exception as analysis_error:
                                    print(f"  ⚠ Could not fully analyze checkpoint: {analysis_error}")
                                    print(f"  Checkpoint has {len(state_dict)} parameter groups")
                            
                            # Don't raise here - let it fall through to checkpoint-only mode
                            # The exception is caught, hf_model_loaded stays False
                        
                        # Try to load checkpoint weights into the model (only if HF model loaded successfully)
                        if hf_model_loaded:
                            try:
                                # Filter state dict to match model architecture
                                model_state_dict = model.state_dict()
                                filtered_state_dict = {}
                                
                                # Match keys from checkpoint to model
                                matched_keys = 0
                                for key, value in state_dict.items():
                                    # Try exact match first
                                    if key in model_state_dict:
                                        if model_state_dict[key].shape == value.shape:
                                            filtered_state_dict[key] = value
                                            matched_keys += 1
                                    else:
                                        # Try removing prefixes (e.g., "model.", "module.")
                                        for prefix in ["model.", "module.", ""]:
                                            clean_key = key.replace(prefix, "", 1) if prefix else key
                                            if clean_key in model_state_dict:
                                                if model_state_dict[clean_key].shape == value.shape:
                                                    filtered_state_dict[clean_key] = value
                                                    matched_keys += 1
                                                    break
                                
                                if matched_keys > 0:
                                    print(f"  ✓ Matched {matched_keys} layers from checkpoint")
                                    model.load_state_dict(filtered_state_dict, strict=False)
                                    print("  ✓ Checkpoint weights loaded into model")
                                    self.model_type = "orpheus_hf"  # Use same generation path as HF
                                    return {
                                        'model': model,
                                        'tokenizer': tokenizer,
                                        'device': self.device,
                                        'checkpoint_path': str(model_path)
                                    }
                                else:
                                    print("  ⚠ Could not match checkpoint keys to model architecture")
                                    print("  Using base model without checkpoint weights")
                                    self.model_type = "orpheus_hf"
                                    return {
                                        'model': model,
                                        'tokenizer': tokenizer,
                                        'device': self.device
                                    }
                            except Exception as e:
                                print(f"  ⚠ Error loading checkpoint weights: {e}")
                                import traceback
                                traceback.print_exc()
                                print("  Using base model without checkpoint weights")
                                self.model_type = "orpheus_hf"
                                return {
                                    'model': model,
                                    'tokenizer': tokenizer,
                                    'device': self.device
                                }
                        else:
                            # HF model didn't load, will fall through to checkpoint-only mode
                            print("  Hugging Face model architecture not available, will use checkpoint-only mode")
                    except Exception as e:
                        print(f"\n  ⚠ Could not load Hugging Face model architecture")
                        print(f"  Error type: {type(e).__name__}")
                        error_msg = str(e)
                        if len(error_msg) > 500:
                            print(f"  Error: {error_msg[:500]}...")
                        else:
                            print(f"  Error: {error_msg}")
                        
                        print("\n  📋 Options to resolve this:")
                        print("  1. Integrate original Orpheus code:")
                        print("     - Clone: https://github.com/asigalov61/Orpheus")
                        print("     - Use their model class to load this checkpoint")
                        print("     - Implement token-to-MIDI conversion")
                        print("  3. Use alternative MusicTransformer:")
                        print("     - Try: gwinndr/MusicTransformer-Pytorch")
                        print("     - Or: jason9693/MusicTransformer-pytorch")
                        print("     - These may have better AutoModel support")
                        print("  4. Use Gradio interface (web-based):")
                        print("     - https://huggingface.co/spaces/asigalov61/Orpheus-Music-Transformer")
                        print("     - No code integration needed")
                        
                        print("\n  ⚠ Falling back to checkpoint-only mode")
                        print("  This checkpoint cannot be used without the original Orpheus model architecture code")
                        print("  MIDI generation will not be available until model architecture is integrated")
                        print("  Returning None - checkpoint stored but unusable without model code")
                        # Don't set model - it can't be used without architecture
                        return None
            
            return None
        except Exception as e:
            raise Exception(f"Orpheus model loading error: {e}")
    
    def _load_generic_musictransformer(self, model_path: Path) -> Optional[Any]:
        """Load generic MusicTransformer-Pytorch model."""
        try:
            # Try importing common MusicTransformer implementations
            checkpoint = torch.load(str(model_path), map_location=self.device)
            
            if isinstance(checkpoint, dict):
                print("  Detected generic MusicTransformer checkpoint")
                self.model_type = "generic"
                return {
                    'state_dict': checkpoint.get('model_state_dict', checkpoint.get('state_dict', checkpoint)),
                    'checkpoint': checkpoint,
                    'device': self.device
                }
            
            return None
        except Exception as e:
            raise Exception(f"Generic MusicTransformer loading error: {e}")
    
    def _init_ipc(self):
        """Initialize IPC pipe for MIDI communication."""
        try:
            if sys.platform == 'win32':
                try:
                    import win32pipe
                    import win32file
                    # Create named pipe
                    self.pipe_name = f"\\\\.\\pipe\\{self.ipc_pipe_name}"
                    # Pipe will be created when needed
                    self.pipe_available = True
                except ImportError:
                    print("Warning: pywin32 not available, IPC disabled")
                    self.pipe_available = False
            else:
                # Unix named pipe
                pipe_path = f"/tmp/{self.ipc_pipe_name}"
                if not os.path.exists(pipe_path):
                    os.mkfifo(pipe_path)
                self.pipe_path = pipe_path
                self.pipe_available = True
        except Exception as e:
            print(f"Warning: Could not initialize IPC: {e}")
            self.pipe_available = False
    
    def _send_midi_to_cpp(self, midi_file: mido.MidiFile) -> bool:
        """Send MIDI data to C++ via IPC."""
        if not self.pipe_available:
            return False
        
        try:
            # Convert MIDI to binary format
            midi_bytes = midi_file.save()
            
            if sys.platform == 'win32':
                try:
                    import win32pipe
                    import win32file
                    try:
                        # Open named pipe
                        handle = win32file.CreateFile(
                            self.pipe_name,
                            win32file.GENERIC_WRITE,
                            0,
                            None,
                            win32file.OPEN_EXISTING,
                            0,
                            None
                        )
                        
                        # Write message header
                        header = struct.pack('IIQ', 1, len(midi_bytes), int(time.time() * 1000))
                        win32file.WriteFile(handle, header, None)
                        
                        # Write MIDI data
                        win32file.WriteFile(handle, midi_bytes, None)
                        
                        win32file.CloseHandle(handle)
                        return True
                    except Exception as e:
                        print(f"Error writing to pipe: {e}")
                        return False
                except ImportError:
                    return False
            else:
                # Unix named pipe
                try:
                    with open(self.pipe_path, 'wb') as f:
                        # Write header
                        header = struct.pack('IIQ', 1, len(midi_bytes), int(time.time() * 1000))
                        f.write(header)
                        f.write(midi_bytes)
                    return True
                except Exception as e:
                    print(f"Error writing to pipe: {e}")
                    return False
        except Exception as e:
            print(f"Error sending MIDI: {e}")
            return False
    
    def generate_midi_pattern(self, context: Dict[str, Any], instrument: str) -> Optional[mido.MidiFile]:
        """Generate MIDI pattern for given instrument and context using transformer."""
        if self.model is None:
            print(f"Error: No transformer model available for {instrument} generation")
            print("  Please configure a valid model in config.yaml")
            return None
        
        try:
            key = context.get('key', 0)
            tempo = context.get('tempo', 120)
            bars = self.generation_length_bars
            mood = context.get('vibe', 'neutral')
            
            # Use transformer model for generation
            midi = self._generate_with_transformer(context, instrument, key, tempo, bars, mood)
            if midi is not None:
                return midi
            else:
                print(f"Error: Transformer generation failed for {instrument}")
                print("  Model is loaded but generation returned None")
                return None
            
        except Exception as e:
            print(f"Error generating MIDI pattern: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_with_transformer(self, context: Dict[str, Any], instrument: str, 
                                   key: int, tempo: float, bars: int, mood: str) -> Optional[mido.MidiFile]:
        """Generate MIDI using transformer model."""
        try:
            if self.model_type == "orpheus_hf" or self.model_type == "orpheus_checkpoint":
                return self._generate_orpheus(context, instrument, key, tempo, bars, mood)
            elif self.model_type == "generic":
                return self._generate_generic_transformer(context, instrument, key, tempo, bars, mood)
            else:
                return None
        except Exception as e:
            print(f"  Transformer generation error: {e}")
            return None
    
    def _generate_orpheus(self, context: Dict[str, Any], instrument: str,
                          key: int, tempo: float, bars: int, mood: str) -> Optional[mido.MidiFile]:
        """Generate MIDI using Orpheus Music Transformer."""
        try:
            if self.model_type == "orpheus_hf":
                # Works for both Hugging Face models and checkpoints loaded into HF architecture
                return self._generate_orpheus_huggingface(context, instrument, key, tempo, bars, mood)
            elif self.model_type == "orpheus_checkpoint":
                # This should not be reached since checkpoint-only mode returns None
                print("  ⚠ Checkpoint-only mode - model architecture code required")
                return None
            else:
                return None
        except Exception as e:
            print(f"  Orpheus generation error: {e}")
            return None
    
    def _generate_orpheus_huggingface(self, context: Dict[str, Any], instrument: str,
                                      key: int, tempo: float, bars: int, mood: str) -> Optional[mido.MidiFile]:
        """Generate MIDI using Orpheus from Hugging Face."""
        try:
            model = self.model['model']
            tokenizer = self.model['tokenizer']
            
            # Create prompt/context for generation
            # Orpheus uses a specific token format - this is a simplified approach
            prompt = f"Generate {instrument} in key {key} at {tempo} BPM, mood: {mood}"
            
            # Tokenize prompt
            inputs = tokenizer(prompt, return_tensors="pt").to(self.device)
            
            # Calculate generation length (approximate tokens for bars)
            # Rough estimate: ~100 tokens per bar
            max_new_tokens = bars * 100
            
            # Generate with sampling
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=0.8,
                    top_p=0.95,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            # Decode tokens
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Convert generated sequence to MIDI
            # Note: This requires the specific token-to-MIDI conversion logic
            # For now, we'll use a placeholder that indicates we need the conversion layer
            print(f"  Generated {len(outputs[0])} tokens for {instrument}")
            
            # TODO: Implement token-to-MIDI conversion
            # This requires understanding Orpheus's token encoding scheme
            print("  Note: Token-to-MIDI conversion not yet implemented")
            print("  See Orpheus documentation for token encoding format")
            print("  Generation cannot complete without token-to-MIDI conversion")
            return None
            
        except Exception as e:
            print(f"  Hugging Face Orpheus generation error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_generic_transformer(self, context: Dict[str, Any], instrument: str,
                                     key: int, tempo: float, bars: int, mood: str) -> Optional[mido.MidiFile]:
        """Generate MIDI using generic MusicTransformer."""
        print(f"  Using generic transformer for {instrument} (key={key}, tempo={tempo}, mood={mood})")
        
        # Placeholder: In production, implement actual MusicTransformer generation
        raise NotImplementedError(
            "Full MusicTransformer generation requires model architecture. "
            "See ml/models/README.md for setup instructions."
        )
    
    
    def run_generator_loop(self):
        """Main generation loop."""
        print("Local generator started")
        
        while self.running:
            try:
                # Check if we need to generate new pattern
                sync_commands = self.ssm.get_sync_commands()
                loop_timer = sync_commands.get('loop_timer', 0.0)
                loop_length = sync_commands.get('loop_length_bars', 8)
                
                # Check if at loop boundary
                current_time = time.time()
                time_since_generation = current_time - self.last_generation_time
                
                # Generate at loop start or after interval
                should_generate = (
                    loop_timer < 0.1 or  # At loop start
                    time_since_generation > self.generation_interval
                )
                
                if should_generate:
                    # Get context from SSM
                    # For MVP, use default context
                    context = {
                        'key': 0.0,  # Would read from SSM
                        'tempo': 120.0,  # Would read from SSM
                    }
                    
                    # Generate MIDI for each instrument
                    for instrument in self.instruments:
                        midi = self.generate_midi_pattern(context, instrument)
                        if midi:
                            # Send to C++
                            if self._send_midi_to_cpp(midi):
                                print(f"Generated and sent {instrument} pattern")
                            self.current_midi = midi
                        else:
                            print(f"Warning: Failed to generate MIDI for {instrument}")
                    
                    self.last_generation_time = current_time
                
                # Sleep to avoid CPU spinning
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in generator loop: {e}")
                time.sleep(0.5)
    
    def start(self):
        """Start the generator thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.run_generator_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the generator thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
