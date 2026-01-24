# Model Checkpoints

To enable full AI music generation, you need to download pre-trained model checkpoints manually and place them in this directory.

## Recommended: Orpheus Music Transformer

The most accessible pre-trained checkpoints are from the **Orpheus Music Transformer** project.

### 1. Download Checkpoints
Visit the Hugging Face repository: [asigalov61/Orpheus-Music-Transformer](https://huggingface.co/asigalov61/Orpheus-Music-Transformer/tree/main)

Download the following files and place them in `ml/models/`:

*   **Main Generation Model**: `Orpheus_Music_Transformer_Trained_Model_96332_steps_0.82_loss_0.748_acc.pth`
*   *(Optional)* **Classifier**: `Orpheus_Music_Transformer_Classifier_Trained_Model_39344_steps_0.2452_loss_0.8904_acc.pth`
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

---
**Note:** These files are ignored by git to keep the repository size manageable.
