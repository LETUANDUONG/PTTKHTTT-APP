"""Bounded in-memory decoding and offline Vietnamese Faster Whisper inference."""
import io
import os
from functools import lru_cache
from threading import Lock

from backend.shared.paths import PROJECT_ROOT
from backend.shared.validation import require

_lock = Lock()
MAX_SECONDS = 15


@lru_cache(maxsize=1)
def _model():
    from faster_whisper import WhisperModel
    path = PROJECT_ROOT / 'models/whisper-small'
    require((path / 'model.bin').is_file(), 'Chưa có model giọng nói. Hãy chạy bước tải model.', 503)
    return WhisperModel(str(path), device='cpu', compute_type='int8',
                        cpu_threads=min(4, os.cpu_count() or 1), local_files_only=True)


def decode_audio(raw):
    import av
    import numpy as np
    require(raw, 'Chưa có âm thanh. Hãy ghi âm lại.')
    require(len(raw) <= 5 * 1024 * 1024, 'Âm thanh tối đa 5 MB.', 413)
    chunks, samples = [], 0
    try:
        with av.open(io.BytesIO(raw)) as audio:
            require(audio.streams.audio, 'File không có âm thanh.')
            resampler = av.AudioResampler(format='fltp', layout='mono', rate=16000)
            for frame in audio.decode(audio=0):
                for converted in resampler.resample(frame):
                    chunk = converted.to_ndarray().flatten()
                    samples += chunk.size
                    require(samples <= MAX_SECONDS * 16000, 'Chỉ ghi âm tối đa 15 giây.', 413)
                    chunks.append(chunk)
            for converted in resampler.resample(None):
                chunk = converted.to_ndarray().flatten()
                samples += chunk.size
                require(samples <= MAX_SECONDS * 16000, 'Chỉ ghi âm tối đa 15 giây.', 413)
                chunks.append(chunk)
    except (av.FFmpegError, ValueError, EOFError):
        require(False, 'Không đọc được âm thanh. Hãy ghi âm lại.')
    require(samples >= 1600, 'Đoạn ghi âm quá ngắn.')
    return np.concatenate(chunks).astype('float32')


def transcribe(raw):
    audio = decode_audio(raw)
    require(abs(audio).max() > 0.0001, 'Không nghe thấy lời nói. Hãy kiểm tra micro.')
    with _lock:
        segments, _ = _model().transcribe(audio, language='vi', vad_filter=True,
                                         condition_on_previous_text=False, beam_size=5,
                                         initial_prompt='Tìm văn phòng phẩm: bút xanh, bút gel, bút bi, sổ tay, giấy A4, Thiên Long.')
        text = ' '.join(segment.text.strip() for segment in segments).strip().rstrip('.,!?;:…').strip()
    require(text, 'Không nghe rõ lời nói. Hãy thử lại gần micro hơn.')
    return {'text': text, 'language': 'vi', 'model': 'faster-whisper-small'}
