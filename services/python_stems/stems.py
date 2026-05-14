import os
import numpy as np
from scipy.signal import butter, filtfilt
from audio_io import read_audio, write_audio

try:
    import torch
    import demucs.api as demucs_api
    DEMUCS_OK = True
except Exception as e:
    DEMUCS_OK = False
    _DEMUCS_ERR = str(e)


def separate_stems(input_path: str, output_dir: str) -> dict:
    """Split audio into vocals, bass, drums, instruments stems."""
    os.makedirs(output_dir, exist_ok=True)
    return _separate_demucs(input_path, output_dir) if DEMUCS_OK \
        else _separate_fallback(input_path, output_dir)


def _separate_demucs(input_path: str, output_dir: str) -> dict:
    separator = demucs_api.Separator(model="htdemucs")
    _, separated = separator.separate_audio_file(input_path)
    stems = {}
    for name, tensor in separated.items():
        out = os.path.join(output_dir, f"{name}.wav")
        demucs_api.save_audio(tensor, out, samplerate=separator.samplerate)
        stems[name] = out
    if "other" in stems:
        new = os.path.join(output_dir, "instruments.wav")
        os.replace(stems.pop("other"), new)
        stems["instruments"] = new
    return stems


def _separate_fallback(input_path: str, output_dir: str) -> dict:
    """Rough mid/side + band-pass stem approximation (no ML)."""
    y, sr = read_audio(input_path)
    if y.ndim == 1:
        y = np.column_stack([y, y])

    L, R = y[:, 0], y[:, 1]
    mid  = (L + R) / 2
    side = (L - R) / 2

    def _stereo(a):
        return np.column_stack([a, a])

    def _lp(sig, cutoff):
        b, a = butter(4, cutoff / (sr / 2), btype="low")
        return filtfilt(b, a, sig)

    def _bp(sig, lo, hi):
        b, a = butter(4, [lo / (sr / 2), hi / (sr / 2)], btype="band")
        return filtfilt(b, a, sig)

    paths = {
        "vocals":      os.path.join(output_dir, "vocals.wav"),
        "bass":        os.path.join(output_dir, "bass.wav"),
        "drums":       os.path.join(output_dir, "drums.wav"),
        "instruments": os.path.join(output_dir, "instruments.wav"),
    }
    write_audio(paths["vocals"],      _stereo(mid),               sr)
    write_audio(paths["bass"],        _stereo(_lp(mid, 250)),      sr)
    write_audio(paths["drums"],       _stereo(_bp(side, 80, 8000)), sr)
    write_audio(paths["instruments"], _stereo(side),               sr)
    return paths
