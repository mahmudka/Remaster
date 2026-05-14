"""Audio I/O via scipy — no libsndfile needed (ARM64 compatible)."""
import os
import subprocess
import tempfile
import numpy as np
from scipy.io import wavfile


def read_audio(path: str) -> tuple[np.ndarray, int]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".wav":
        return _read_wav(path)
    tmp = tempfile.mktemp(suffix=".wav")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", path, "-ar", "44100", "-ac", "2", tmp],
            check=True, capture_output=True
        )
        return _read_wav(tmp)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def write_audio(path: str, data: np.ndarray, sr: int):
    pcm = np.clip(data, -1.0, 1.0)
    pcm24 = (pcm * 8388607).astype(np.int32)
    wavfile.write(path, sr, pcm24)


def _read_wav(path: str) -> tuple[np.ndarray, int]:
    sr, data = wavfile.read(path)
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 8388608.0
    elif data.dtype != np.float32:
        data = data.astype(np.float32)
    if data.ndim == 1:
        data = np.column_stack([data, data])
    return data, sr
