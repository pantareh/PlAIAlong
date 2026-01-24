# Model Checkpoints

To enable full AI music generation, you need to download pre-trained model checkpoints manually and place them in this directory.

## Recommended: Orpheus Music Transformer

The most accessible pre-trained checkpoints are from the **Orpheus Music Transformer** project.

⚠️ **Important Note**: The Orpheus model on Hugging Face (`asigalov61/Orpheus-Music-Transformer`) is **not available in standard AutoModel format**. It requires custom model code from the original repository. 

**Options:**
1. **Use local checkpoint files** (recommended) - Download checkpoints and use with original Orpheus code
2. **Use Gradio interface** - Access via web interface at the Hugging Face space
3. **Use alternative MusicTransformer** - See "Alternatives" section below

### 1. Download Checkpoints
Visit the Hugging Face repository: [asigalov61/Orpheus-Music-Transformer](https://huggingface.co/asigalov61/Orpheus-Music-Transformer/tree/main)

Download the following files and place them in `ml/models/`:

*   **Main Generation Model** (REQUIRED for MIDI generation): 
    - `Orpheus_Music_Transformer_Trained_Model_96332_steps_0.82_loss_0.748_acc.pth`
    - ⚠️ **Important**: You need the **generation model**, not the classifier!
*   *(Optional)* **Classifier**: `Orpheus_Music_Transformer_Classifier_Trained_Model_39344_steps_0.2452_loss_0.8904_acc.pth`
    - ⚠️ **Note**: Classifier models are for classification tasks, NOT for MIDI generation
*   *(Optional)* **Bridge Model**: `Orpheus_Bridge_Music_Transformer_Trained_Model_19571_steps_0.9396_loss_0.7365_acc.pth`

### 2. Update Configuration
Once downloaded, update your `ml/config/config.yaml` to point to the main model file:

```yaml
local_generator:
  model_path: "models/Orpheus_Music_Transformer_Trained_Model_96332_steps_0.82_loss_0.748_acc.pth"
```

## Alternatives

You can also use checkpoints from these implementations:
*   [gwinndr/MusicTransformer-Pytorch](https://github.com/gwinndr/MusicTransformer-Pytorch)
*   [jason9693/MusicTransformer-pytorch](https://github.com/jason9693/MusicTransformer-pytorch)

If you use a different implementation, you may need to update `ml/src/local_generator.py` to match the specific model architecture and loading logic.

## Implementation Status

The `LocalGenerator` class has been updated to support transformer-based generation:

✅ **Implemented:**
- Model checkpoint loading (Hugging Face and local `.pth` files)
- Model detection and initialization
- Token generation using transformer models
- Graceful fallback to rule-based generation when model unavailable

⚠️ **Requires Implementation:**
- **Token-to-MIDI conversion**: The generated token sequences need to be converted to MIDI format
  - This requires understanding the specific token encoding scheme used by your model
  - Orpheus uses a custom token format (3 tokens per note, 7 tokens per tri-chord)
  - You'll need to implement the decoder logic in `_generate_orpheus_huggingface()` method

📝 **To Complete Transformer Integration:**

1. **For Orpheus Models:**
   - Study the Orpheus token encoding format from the [Hugging Face repository](https://huggingface.co/asigalov61/Orpheus-Music-Transformer)
   - Implement token-to-MIDI conversion in `local_generator.py`
   - Test with sample token sequences

2. **For Other Models:**
   - Follow the model's documentation for token encoding
   - Implement conversion logic in `_generate_generic_transformer()` method

3. **Alternative: Use Model's Official Interface**
   - Some models provide Python APIs or scripts for generation
   - You can call these from `LocalGenerator` instead of implementing token conversion

**Current Behavior:**
- If a model is loaded successfully, it will attempt transformer generation
- If token-to-MIDI conversion fails or model is unavailable, the system automatically falls back to rule-based pattern generation
- This ensures the system always produces MIDI output, even without a working transformer

---
**Note:** These files are ignored by git to keep the repository size manageable.
