import torch
import os

# Path to the original checkpoint
original_checkpoint_path = "/Volumes/One Touch/AI_MODEL/neuscraper-v1-clueweb/training_state_checkpoint.tar"

# Path to save the fixed checkpoint
fixed_checkpoint_path = "/Volumes/One Touch/AI_MODEL/neuscraper-v1-clueweb/fixed_training_state_checkpoint.tar"

print("Loading checkpoint...")
checkpoint = torch.load(original_checkpoint_path, map_location='cpu', weights_only=False)
state_dict = checkpoint["model_state_dict"]

print("Keys in original state dict:", len(state_dict))

# Remove problematic keys
problematic_keys = [
    "text_roberta.embeddings.position_ids"
]

for key in problematic_keys:
    if key in state_dict:
        print(f"Removing key: {key}")
        del state_dict[key]
    else:
        print(f"Key not found: {key}")

print("Keys in updated state dict:", len(state_dict))

# Update the checkpoint with the modified state dict
checkpoint["model_state_dict"] = state_dict

# Save the updated checkpoint
print(f"Saving updated checkpoint to {fixed_checkpoint_path}")
torch.save(checkpoint, fixed_checkpoint_path)
print("Done!")