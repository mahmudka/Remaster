"""
Mastering engine: multiband compression → limiter → LUFS normalisation.
Target: -14 LUFS integrated (Spotify standard).
"""
import numpy as np
from scipy.signal import butter, filtfilt
from audio_io import read_audio, write_audio
from mix_engine import apply_compression


TARGET_LUFS = -14.0


# ── LUFS measurement ──────────────────────────────────────────────────────────

def measure_lufs(y: np.ndarray, sr: int) -> tuple[float, float]:
    """Returns (integrated LUFS, true peak dBFS)."""
    # K-weighting pre-filter (stage 1: high-shelf)
    b1 = np.array([1.53512485958697, -2.69169618940638, 1.19839281085285])
    a1 = np.array([1.0, -1.69065929318241, 0.73248077421585])
    # K-weighting pre-filter (stage 2: high-pass)
    b2 = np.array([1.0, -2.0, 1.0])
    a2 = np.array([1.0, -1.99004745483398, 0.99007225036289])

    mono = y.mean(axis=1) if y.ndim == 2 else y
    try:
        w = filtfilt(b1, a1, mono)
        w = filtfilt(b2, a2, w)
    except Exception:
        w = mono

    block = int(sr * 0.4)
    if len(w) < block:
        mean_sq = float(np.mean(w ** 2))
    else:
        n_blocks  = len(w) // block
        blocks_sq = [np.mean(w[i*block:(i+1)*block]**2) for i in range(n_blocks)]
        # Gating: discard blocks below threshold (-70 LUFS relative)
        threshold = max(blocks_sq) * 1e-7
        gated     = [b for b in blocks_sq if b > threshold]
        mean_sq   = float(np.mean(gated)) if gated else float(np.mean(blocks_sq))

    lufs       = -0.691 + 10 * np.log10(mean_sq + 1e-12)
    true_peak  = float(20 * np.log10(np.max(np.abs(y)) + 1e-12))
    return round(float(lufs), 2), round(true_peak, 2)


# ── Multiband compression ─────────────────────────────────────────────────────

def multiband_compress(y: np.ndarray, sr: int) -> np.ndarray:
    """Three-band compression: sub+bass / mids / highs."""
    def _band(lo, hi):
        if lo is None:
            b, a = butter(4, hi / (sr / 2), btype="low")
        elif hi is None:
            b, a = butter(4, lo / (sr / 2), btype="high")
        else:
            b, a = butter(4, [lo / (sr / 2), hi / (sr / 2)], btype="band")
        return filtfilt(b, a, y, axis=0)

    low  = _band(None, 250)
    mid  = _band(250, 4000)
    high = _band(4000, None)

    low  = apply_compression(low,  sr, threshold_db=-20, ratio=4,   attack_ms=5,   release_ms=80)
    mid  = apply_compression(mid,  sr, threshold_db=-18, ratio=3,   attack_ms=10,  release_ms=120)
    high = apply_compression(high, sr, threshold_db=-16, ratio=2.5, attack_ms=15,  release_ms=150)

    return np.clip(low + mid + high, -1.0, 1.0)


# ── Limiter ───────────────────────────────────────────────────────────────────

def apply_limiter(y: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    ceiling = 10 ** (ceiling_db / 20)
    peak    = np.max(np.abs(y))
    if peak > ceiling:
        y = y * (ceiling / peak)
    return np.clip(y, -ceiling, ceiling)


# ── LUFS normalisation ────────────────────────────────────────────────────────

def normalise_lufs(y: np.ndarray, sr: int,
                   target: float = TARGET_LUFS) -> np.ndarray:
    current, _ = measure_lufs(y, sr)
    gain_db     = target - current
    gain_lin    = 10 ** (gain_db / 20)
    return np.clip(y * gain_lin, -1.0, 1.0)


# ── Full mastering pipeline ───────────────────────────────────────────────────

def master_track(input_path: str, output_path: str,
                 target_lufs: float = TARGET_LUFS) -> dict:
    y, sr = read_audio(input_path)

    y = multiband_compress(y, sr)
    y = normalise_lufs(y, sr, target_lufs)
    y = apply_limiter(y, ceiling_db=-1.0)

    lufs_i, lufs_tp = measure_lufs(y, sr)
    write_audio(output_path, y, sr)

    return {
        "output":          output_path,
        "lufs_integrated": lufs_i,
        "lufs_true_peak":  lufs_tp,
        "target_lufs":     target_lufs,
    }
