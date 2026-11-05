"""Download inference weights once; runtime containers mount them read-only."""
from pathlib import Path

from huggingface_hub import snapshot_download


ROOT = Path(__file__).resolve().parents[1] / 'models'
for repo, folder, files in [
    ('Systran/faster-whisper-small', 'whisper-small', ['*.json', '*.txt', 'model.bin']),
    ('sentence-transformers/clip-ViT-B-32', 'clip-vit-b32', ['*.json', '*.txt', '*.safetensors']),
]:
    snapshot_download(repo, local_dir=ROOT / folder, allow_patterns=files, max_workers=2)
    print(f'Ready: {folder}', flush=True)
