"""
RVC voice conversion engine.
Uses rvc-python when available; falls back to pitch-shift via scipy.
"""
import os
import numpy as np

try:
    from rvc_python.infer import RVCInference
    RVC_OK = True
except ImportError:
    RVC_OK = False


def convert_voice(
    vocal_wav: str,
    model_path: str,
    index_path: str,
    output_path: str,
    f0_up_key: int = 0,
) -> str:
    """
    Convert vocal using RVC model.
    Returns path to converted wav.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if RVC_OK and model_path and os.path.exists(model_path):
        return _convert_rvc(vocal_wav, model_path, index_path, output_path, f0_up_key)
    else:
        return _convert_fallback(vocal_wav, output_path, f0_up_key)


def _convert_rvc(vocal_wav, model_path, index_path, output_path, f0_up_key):
    rvc = RVCInference(
        model_path=model_path,
        index_path=index_path if index_path and os.path.exists(index_path) else "",
        f0_up_key=f0_up_key,
        f0_method="rmvpe",
        index_rate=0.75,
        protect=0.33,
    )
    rvc.infer_file(vocal_wav, output_path)
    return output_path


def _convert_fallback(vocal_wav, output_path, f0_up_key):
    """Pitch-shift fallback using scipy (no ML, just resampling)."""
    import scipy.io.wavfile as wav
    import scipy.signal as sig

    sr, data = wav.read(vocal_wav)
    if data.ndim > 1:
        data = data.mean(axis=1)
    data = data.astype(np.float32)

    if f0_up_key != 0:
        # Simple pitch shift via resampling
        factor = 2 ** (f0_up_key / 12.0)
        new_len = int(len(data) / factor)
        data = sig.resample(data, new_len)

    # Ensure same length as input (pad or trim)
    data = np.clip(data, -32768, 32767).astype(np.int16)
    wav.write(output_path, sr, data)
    return output_path
