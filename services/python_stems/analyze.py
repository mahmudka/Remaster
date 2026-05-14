import json
import numpy as np
from audio_io import read_audio

try:
    import librosa
    LIBROSA_OK = True
except Exception:
    LIBROSA_OK = False


def analyze_track(file_path: str) -> dict:
    """Extract BPM, key, genre hint and spectral profile from audio file."""
    y, sr = read_audio(file_path)
    if y.ndim == 2:
        mono = y.mean(axis=1)
    else:
        mono = y

    bpm   = _detect_bpm(mono, sr)
    key   = _detect_key(mono, sr)
    genre = _guess_genre(bpm)

    return {
        "bpm": round(bpm, 1),
        "key": key,
        "genre": genre,
        "frequency_map":    _frequency_map(mono, sr),
        "dynamics_profile": _dynamics_profile(mono),
        "stereo_profile":   _stereo_profile(y),
    }


def _detect_bpm(y: np.ndarray, sr: int) -> float:
    if LIBROSA_OK:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        return float(tempo[0] if hasattr(tempo, "__len__") else tempo)
    # Autocorrelation fallback
    chunk = y[:sr * 4]
    corr = np.correlate(chunk, chunk, mode="full")[len(chunk) - 1:]
    lo, hi = int(sr * 60 / 180), int(sr * 60 / 60)
    if hi <= lo:
        return 120.0
    peak = lo + int(np.argmax(corr[lo:hi]))
    return round(60.0 * sr / peak, 1) if peak > 0 else 120.0


def _detect_key(y: np.ndarray, sr: int) -> str:
    if LIBROSA_OK:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        notes  = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
        return notes[int(np.argmax(chroma.mean(axis=1)))]
    return "C"


def _guess_genre(bpm: float) -> str:
    if bpm < 85:  return "ballad"
    if bpm < 100: return "hip-hop"
    if bpm < 125: return "pop"
    if bpm < 145: return "house"
    return "edm"


def _frequency_map(y: np.ndarray, sr: int) -> str:
    n_fft = 2048
    spec  = np.abs(np.fft.rfft(y[:n_fft]))
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    bands = {
        "sub_bass": (20,   80),
        "bass":     (80,   250),
        "low_mid":  (250,  500),
        "mid":      (500,  2000),
        "high_mid": (2000, 6000),
        "air":      (6000, 20000),
    }
    return json.dumps({
        name: round(float(spec[(freqs >= lo) & (freqs < hi)].mean()), 4)
        for name, (lo, hi) in bands.items()
    })


def _dynamics_profile(y: np.ndarray) -> str:
    rms  = float(np.sqrt(np.mean(y ** 2)))
    peak = float(np.max(np.abs(y)))
    crest = round(20 * np.log10(peak / (rms + 1e-9)), 2)
    return json.dumps({"rms": round(rms, 4), "peak": round(peak, 4), "crest_factor_db": crest})


def _stereo_profile(y: np.ndarray) -> str:
    if y.ndim < 2 or y.shape[1] < 2:
        return json.dumps({"width": 0.0, "mono": True})
    L, R  = y[:, 0], y[:, 1]
    mid   = (L + R) / 2
    side  = (L - R) / 2
    width = float(np.sqrt(np.mean(side**2)) / (np.sqrt(np.mean(mid**2)) + 1e-9))
    return json.dumps({"width": round(width, 4), "mono": False})
