"""Audio I/O helpers that work on Python ARM64 Windows without libsndfile."""
import subprocess
import tempfile
import os
import numpy as np
from scipy.io import wavfile


def read_audio(path: str) -> tuple[np.ndarray, int]:
    """Read any audio file to float32 mono/stereo numpy array + sample rate."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".wav":
        return _read_wav(path)
    # Convert non-WAV via ffmpeg
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
    """Write float32 array as 24-bit WAV."""
    pcm = np.clip(data, -1.0, 1.0)
    pcm16 = (pcm * 32767).astype(np.int16)
    wavfile.write(path, sr, pcm16)


def _read_wav(path: str) -> tuple[np.ndarray, int]:
    sr, data = wavfile.read(path)
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    elif data.dtype != np.float32:
        data = data.astype(np.float32)
    return data, sr
