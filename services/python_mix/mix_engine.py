"""
Mix engine: EQ → compression → balance → bus → reverb → delay.
Reverb and delay are applied ONLY on the assembled mix, never on individual stems.
"""
import numpy as np
from scipy.signal import butter, filtfilt, sosfilt, butter as _butter
from audio_io import read_audio, write_audio


# ── EQ ────────────────────────────────────────────────────────────────────────

def apply_eq(y: np.ndarray, sr: int, bands: list[dict]) -> np.ndarray:
    """bands: [{freq, gain_db, q, type}]  type: peak|low_shelf|high_shelf|hp|lp"""
    out = y.copy()
    for band in bands:
        out = _apply_band(out, sr, band)
    return out


def _apply_band(y, sr, band):
    freq     = float(band.get("freq", 1000))
    gain_db  = float(band.get("gain_db", 0))
    btype    = band.get("type", "peak")
    nyq      = sr / 2
    norm     = min(freq / nyq, 0.99)

    if btype in ("hp", "highpass"):
        b, a = butter(2, norm, btype="high")
    elif btype in ("lp", "lowpass"):
        b, a = butter(2, norm, btype="low")
    else:
        # Simple gain shelf/peak via low-pass complement
        gain = 10 ** (gain_db / 20)
        b, a = butter(2, norm, btype="low")
        lp = filtfilt(b, a, y, axis=0)
        hp = y - lp
        return lp * gain + hp

    return filtfilt(b, a, y, axis=0)


# ── Compression ───────────────────────────────────────────────────────────────

def apply_compression(y: np.ndarray, sr: int,
                      threshold_db: float = -18.0,
                      ratio: float = 4.0,
                      attack_ms: float = 10.0,
                      release_ms: float = 100.0,
                      makeup_db: float = 0.0) -> np.ndarray:
    threshold = 10 ** (threshold_db / 20)
    makeup    = 10 ** (makeup_db / 20)
    attack    = int(sr * attack_ms / 1000)
    release   = int(sr * release_ms / 1000)

    mono  = y.mean(axis=1) if y.ndim == 2 else y
    level = np.abs(mono)
    gain  = np.ones_like(level)

    env = 0.0
    for i in range(len(level)):
        target = level[i]
        coeff = (1 / attack) if target > env else (1 / release)
        env += coeff * (target - env)
        if env > threshold:
            reduction = threshold + (env - threshold) / ratio
            gain[i] = reduction / (env + 1e-9)

    if y.ndim == 2:
        gain = gain[:, np.newaxis]
    return np.clip(y * gain * makeup, -1.0, 1.0)


# ── Balance & Pan ──────────────────────────────────────────────────────────────

def apply_gain(y: np.ndarray, gain_db: float) -> np.ndarray:
    return y * (10 ** (gain_db / 20))


def apply_pan(y: np.ndarray, pan: float) -> np.ndarray:
    """pan: -1 (full left) … 0 (center) … +1 (full right)"""
    if y.ndim == 1:
        y = np.column_stack([y, y])
    l_gain = np.cos((pan + 1) * np.pi / 4)
    r_gain = np.sin((pan + 1) * np.pi / 4)
    out = y.copy()
    out[:, 0] *= l_gain
    out[:, 1] *= r_gain
    return out


# ── Reverb (mix-only) ─────────────────────────────────────────────────────────

def apply_reverb(y: np.ndarray, sr: int,
                 room_size: float = 0.5,
                 wet: float = 0.2) -> np.ndarray:
    """Simple Schroeder reverb — applied on assembled mix only."""
    delay_samples = [
        int(sr * 0.030 * (1 + room_size * 0.4)),
        int(sr * 0.037 * (1 + room_size * 0.4)),
        int(sr * 0.043 * (1 + room_size * 0.4)),
        int(sr * 0.050 * (1 + room_size * 0.4)),
    ]
    g = 0.55 + room_size * 0.25
    out = np.zeros_like(y)
    for d in delay_samples:
        buf = np.zeros((d, y.shape[1] if y.ndim == 2 else 1))
        sig = y if y.ndim == 2 else y[:, np.newaxis]
        rev = np.zeros_like(sig)
        for i in range(len(sig)):
            idx  = i % d
            feed = buf[idx].copy()
            buf[idx] = sig[i] + g * feed
            rev[i]  = feed
        if y.ndim == 1:
            out += rev[:, 0]
        else:
            out += rev
    return np.clip(y * (1 - wet) + out * wet, -1.0, 1.0)


# ── Delay (mix-only) ──────────────────────────────────────────────────────────

def apply_delay(y: np.ndarray, sr: int,
                delay_ms: float = 250.0,
                feedback: float = 0.3,
                wet: float = 0.2) -> np.ndarray:
    """Stereo ping-pong delay — applied on assembled mix only."""
    d = int(sr * delay_ms / 1000)
    if d >= len(y):
        return y
    sig  = y if y.ndim == 2 else np.column_stack([y, y])
    buf  = np.zeros_like(sig)
    out  = sig.copy()
    echo = np.zeros_like(sig)
    echo[d:] = sig[:-d] * wet
    for i in range(d, len(sig)):
        echo[i] += echo[i - d] * feedback
    return np.clip(sig + echo, -1.0, 1.0)


# ── Full mix pipeline ──────────────────────────────────────────────────────────

def mix_stems(stems: dict, plan: dict, output_path: str, sr: int = 44100) -> str:
    """
    stems: {"vocals": path, "bass": path, "drums": path, "instruments": path}
    plan:  MixPlan dict from KnowledgeAgent
    """
    tracks_plan = {t["track"]: t for t in plan.get("tracks", [])}
    mixed = None

    for stem_name, stem_path in stems.items():
        y, file_sr = read_audio(stem_path)
        if file_sr != sr:
            # Simple resample via linear interpolation
            from scipy.signal import resample_poly
            from math import gcd
            g = gcd(sr, file_sr)
            y = resample_poly(y, sr // g, file_sr // g, axis=0)

        tp = tracks_plan.get(stem_name, {})

        # EQ
        if "eq" in tp:
            y = apply_eq(y, sr, tp["eq"])

        # Compression
        comp = tp.get("comp", {})
        y = apply_compression(
            y, sr,
            threshold_db = float(comp.get("threshold_db", -18)),
            ratio        = float(comp.get("ratio", 3)),
            attack_ms    = float(comp.get("attack_ms", 10)),
            release_ms   = float(comp.get("release_ms", 100)),
            makeup_db    = float(comp.get("makeup_db", 0)),
        )

        # Gain & pan
        y = apply_gain(y, float(tp.get("gain_db", 0)))
        y = apply_pan(y, float(tp.get("pan", 0)))

        mixed = y if mixed is None else mixed + y

    if mixed is None:
        raise ValueError("No stems provided")

    # Normalise before bus processing
    peak = np.max(np.abs(mixed))
    if peak > 0:
        mixed = mixed / peak * 0.9

    # Bus compression
    bus = plan.get("bus", {})
    if bus:
        mixed = apply_compression(
            mixed, sr,
            threshold_db = float(bus.get("threshold_db", -12)),
            ratio        = float(bus.get("ratio", 2)),
            attack_ms    = float(bus.get("attack_ms", 20)),
            release_ms   = float(bus.get("release_ms", 200)),
        )

    # Reverb — mix only, not stems
    rev = plan.get("reverb", {})
    if rev and float(rev.get("wet", 0)) > 0:
        mixed = apply_reverb(
            mixed, sr,
            room_size = float(rev.get("room_size", 0.5)),
            wet       = float(rev.get("wet", 0.15)),
        )

    # Delay — mix only, not stems
    dly = plan.get("delay", {})
    if dly and float(dly.get("wet", 0)) > 0:
        mixed = apply_delay(
            mixed, sr,
            delay_ms = float(dly.get("delay_ms", 250)),
            feedback = float(dly.get("feedback", 0.3)),
            wet      = float(dly.get("wet", 0.2)),
        )

    write_audio(output_path, mixed, sr)
    return output_path
