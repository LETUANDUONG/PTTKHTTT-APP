"""Offline CLIP embeddings; validated uploads are processed only in memory."""
import io
import warnings
from functools import lru_cache
from threading import Lock

from PIL import Image, ImageOps, UnidentifiedImageError

from backend.shared.validation import require
from backend.shared.paths import PROJECT_ROOT

_lock = Lock()


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    import torch
    path = PROJECT_ROOT / 'models/clip-vit-b32'
    require((path / 'modules.json').is_file(), 'Chưa có model tìm ảnh. Hãy chạy bước tải model.', 503)
    torch.set_num_threads(4)
    return SentenceTransformer(str(path), device='cpu', local_files_only=True)


def descriptor(image):
    with _lock:
        return _model().encode(ImageOps.exif_transpose(image).convert('RGB'),
                               normalize_embeddings=True).tolist()


def encode_query(raw):
    require(len(raw)<=5*1024*1024,'Ảnh tối đa 5 MB.',413)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                require(image.format in ['JPEG','PNG','WEBP'],'Định dạng ảnh không hỗ trợ.')
                require(image.width*image.height<=16000000,'Ảnh tối đa 16 triệu pixel.')
                image.load()
                prepared=ImageOps.exif_transpose(image).convert('RGB')
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        require(False,'Không đọc được ảnh. Thử ảnh khác hoặc tìm bằng từ khoá.')
    return descriptor(prepared)


@lru_cache(maxsize=256)
def _cached_catalogue(path, modified, size):
    with Image.open(path) as image:
        return descriptor(image)


def encode_catalogue(path):
    stat = path.stat()
    return _cached_catalogue(str(path), stat.st_mtime_ns, stat.st_size)
