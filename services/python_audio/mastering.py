"""
Audio mastering DSP chain.
Order: declip → denoise → EQ → compression → transient → de-ess →
       stereo correction → HF enhance → LUFS normalise → true-peak limit.
"""

from __future__ import annotations
import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from scipy import signal


# ── I/O ───────────────────────────────────────────────────────────────────────

def load_wav(path: str) -> tuple[np.ndarray, int]:
    data, sr = sf.read(path, dtype="float32", always_2d=True)
    return data, sr


def save_wav(path: str, audio: np.ndarray, sr: int) -> None:
    # Clip to prevent accidental overflow before save
    audio = np.clip(audio, -1.0, 1.0)
    sf.write(path, audio, sr, subtype="PCM_24")


# ── Declip ────────────────────────────────────────────────────────────────────

def declip(audio: np.ndarray, threshold: float = 0.99) -> np.ndarray:
    """Simple soft-knee declipping via cubic spline interpolation at clipped samples."""
    out = audio.copy()
    for ch in range(out.shape[1]):
        clip_mask = np.abs(out[:, ch]) >= threshold
        if not clip_mask.any():
            continue
        indices = np.arange(len(out))
        good = ~clip_mask
        if good.sum() < 4:
            continue
        from scipy.interpolate import interp1d
        interp = interp1d(indices[good], out[good, ch], kind="cubic",
                          bounds_error=False, fill_value="extrapolate")
        out[clip_mask, ch] = np.clip(interp(indices[clip_mask]), -1.0, 1.0)
    return out


# ── Denoise ───────────────────────────────────────────────────────────────────

def denoise(audio: np.ndarray, sr: int, prop_decrease: float = 0.85) -> np.ndarray:
    try:
        import noisereduce as nr
        out = np.zeros_like(audio)
        for ch in range(audio.shape[1]):
            out[:, ch] = nr.reduce_noise(
                y=audio[:, ch].astype(np.float32),
                sr=sr,
                prop_decrease=prop_decrease,
                stationary=False,
            )
        return out.astype(np.float32)
    except Exception:
        return audio


# ── EQ ────────────────────────────────────────────────────────────────────────

def apply_eq(audio: np.ndarray, sr: int, bands: list[dict]) -> np.ndarray:
    """Apply parametric EQ bands (peak, shelf, highpass, lowpass)."""
    out = audio.copy()
    for band in bands:
        freq  = float(band.get("frequency", 1000))
        gain  = float(band.get("gain", 0))
        q     = float(band.get("q", 1.0))
        btype = str(band.get("type", "peak")).lower()

        if abs(gain) < 0.01 and btype not in ("highpass", "lowpass"):
            continue

        nyq = sr / 2.0
        norm_freq = min(freq / nyq, 0.999)

        try:
            if btype == "peak":
                b, a = _peaking_eq(freq, gain, q, sr)
            elif btype in ("highshelf", "shelf"):
                b, a = signal.iirfilter(2, norm_freq, btype="high",
                                        ftype="butter", output="ba")
                # Scale output by gain
                b = b * (10 ** (gain / 20))
            elif btype == "highpass":
                b, a = signal.butter(2, norm_freq, btype="highpass")
            elif btype == "lowpass":
                b, a = signal.butter(2, norm_freq, btype="lowpass")
            else:
                b, a = _peaking_eq(freq, gain, q, sr)

            for ch in range(out.shape[1]):
                out[:, ch] = signal.lfilter(b, a, out[:, ch]).astype(np.float32)
        except Exception:
            continue

    return out


def _peaking_eq(freq: float, gain_db: float, q: float, sr: int):
    """RBJ Audio EQ cookbook — peaking EQ filter."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * freq / sr
    alpha = np.sin(w0) / (2 * q)

    b0 =  1 + alpha * A
    b1 = -2 * np.cos(w0)
    b2 =  1 - alpha * A
    a0 =  1 + alpha / A
    a1 = -2 * np.cos(w0)
    a2 =  1 - alpha / A

    b = np.array([b0, b1, b2]) / a0
    a = np.array([a0, a1, a2]) / a0
    return b, a


# ── Compression ───────────────────────────────────────────────────────────────

def apply_compression(
    audio: np.ndarray, sr: int,
    threshold_db: float = -20.0,
    ratio: float = 2.0,
    attack_ms: float = 15.0,
    release_ms: float = 100.0,
    expand: bool = False,
) -> np.ndarray:
    """Simple feed-forward RMS compressor / expander."""
    try:
        from pedalboard import Pedalboard, Compressor
        board = Pedalboard([
            Compressor(
                threshold_db=threshold_db,
                ratio=ratio,
                attack_ms=attack_ms,
                release_ms=release_ms,
            )
        ])
        stereo = audio.T.astype(np.float32)  # (channels, samples)
        processed = board(stereo, sr)
        return processed.T.astype(np.float32)
    except Exception:
        return audio


# ── Transient shaping ─────────────────────────────────────────────────────────

def apply_transient_shape(audio: np.ndarray, sr: int, attack_gain: float = 2.0) -> np.ndarray:
    """Enhance transients by boosting onset envelope."""
    try:
        import librosa
        out = np.zeros_like(audio)
        for ch in range(audio.shape[1]):
            mono = audio[:, ch].astype(np.float32)
            onset_env = librosa.onset.onset_strength(y=mono, sr=sr)
            # Resample envelope to audio length
            env_up = np.interp(
                np.linspace(0, len(onset_env), len(mono)),
                np.arange(len(onset_env)),
                onset_env
            )
            # Normalise envelope and blend
            env_up = (env_up - env_up.min()) / (env_up.max() - env_up.min() + 1e-9)
            gain = 1.0 + env_up * (attack_gain - 1.0)
            out[:, ch] = (mono * gain.astype(np.float32))
        return np.clip(out, -1.0, 1.0).astype(np.float32)
    except Exception:
        return audio


# ── De-esser ──────────────────────────────────────────────────────────────────

def apply_deess(audio: np.ndarray, sr: int,
                freq_lo: float = 5500, freq_hi: float = 8000,
                threshold_db: float = -20.0) -> np.ndarray:
    """Frequency-selective compression in the sibilance range."""
    out = audio.copy()
    nyq = sr / 2.0
    lo  = min(freq_lo / nyq, 0.99)
    hi  = min(freq_hi / nyq, 0.99)
    if lo >= hi:
        return out
    try:
        b, a = signal.butter(4, [lo, hi], btype="bandpass")
        threshold_lin = 10 ** (threshold_db / 20)
        for ch in range(out.shape[1]):
            sib = signal.lfilter(b, a, out[:, ch])
            env = np.abs(signal.hilbert(sib))
            gain = np.where(env > threshold_lin, threshold_lin / np.maximum(env, 1e-9), 1.0)
            gain = np.clip(gain, 0.1, 1.0)
            out[:, ch] = (out[:, ch] * gain).astype(np.float32)
    except Exception:
        pass
    return out


# ── Stereo correction ─────────────────────────────────────────────────────────

def apply_stereo_width(audio: np.ndarray, width: float) -> np.ndarray:
    """Mid/side width control. width=1.0 = original, 0=mono, 2.0=double width."""
    if audio.shape[1] < 2:
        return audio
    L = audio[:, 0].astype(np.float64)
    R = audio[:, 1].astype(np.float64)
    mid  = (L + R) * 0.5
    side = (L - R) * 0.5 * width
    out = audio.copy()
    out[:, 0] = np.clip(mid + side, -1.0, 1.0).astype(np.float32)
    out[:, 1] = np.clip(mid - side, -1.0, 1.0).astype(np.float32)
    return out


def apply_mono_below_hz(audio: np.ndarray, sr: int, freq: float) -> np.ndarray:
    """Sum L+R to mono below specified frequency (sub-bass mono)."""
    if audio.shape[1] < 2:
        return audio
    nyq = sr / 2.0
    norm_freq = min(freq / nyq, 0.99)
    try:
        b, a = signal.butter(4, norm_freq, btype="lowpass")
        out = audio.copy()
        for ch in range(out.shape[1]):
            low = signal.lfilter(b, a, audio[:, ch])
            high = audio[:, ch] - low
            mono_low = signal.lfilter(b, a, (audio[:, 0] + audio[:, 1]) * 0.5)
            out[:, ch] = (mono_low + high).astype(np.float32)
        return out
    except Exception:
        return audio


# ── HF enhancement ────────────────────────────────────────────────────────────

def apply_hf_gain(audio: np.ndarray, sr: int, gain_db: float) -> np.ndarray:
    nyq = sr / 2.0
    norm_freq = min(12000 / nyq, 0.99)
    try:
        b, a = signal.butter(2, norm_freq, btype="highpass")
        out = audio.copy()
        gain_lin = 10 ** (gain_db / 20)
        for ch in range(out.shape[1]):
            hf = signal.lfilter(b, a, audio[:, ch])
            lf = audio[:, ch] - hf
            out[:, ch] = (lf + hf * gain_lin).astype(np.float32)
        return out
    except Exception:
        return audio


# ── LUFS normalisation (double-pass) ─────────────────────────────────────────

def lufs_normalise(audio: np.ndarray, sr: int, target_lufs: float, max_gain_db: float = 24.0) -> np.ndarray:
    """
    Double-pass LUFS normalization.
    Pass 1: compute gain needed, apply.
    Pass 2: re-measure, apply residual correction (handles limiter-induced gain reduction).
    """
    meter = pyln.Meter(sr)
    mono = audio.mean(axis=1).astype(np.float64)

    for _pass in range(2):
        current_lufs = meter.integrated_loudness(mono)
        if not np.isfinite(current_lufs):
            break
        delta_db = target_lufs - current_lufs
        if abs(delta_db) < 0.3:
            break
        # Clamp to avoid insane gains on very quiet files
        delta_db = np.clip(delta_db, -max_gain_db, max_gain_db)
        gain_lin = float(10 ** (delta_db / 20))
        audio = (audio * gain_lin).astype(np.float32)
        mono  = audio.mean(axis=1).astype(np.float64)

    return audio


# ── True-peak limiter ─────────────────────────────────────────────────────────

def true_peak_limit(audio: np.ndarray, sr: int, ceiling_db: float = -1.0, release_ms: float = 50.0) -> np.ndarray:
    """Simple brick-wall true-peak limiter via pedalboard, falls back to hard clip."""
    ceiling_lin = 10 ** (ceiling_db / 20)
    try:
        from pedalboard import Pedalboard, Limiter
        board = Pedalboard([Limiter(threshold_db=ceiling_db, release_ms=release_ms)])
        stereo = audio.T.astype(np.float32)
        result = board(stereo, sr)
        return result.T.astype(np.float32)
    except Exception:
        return np.clip(audio, -ceiling_lin, ceiling_lin).astype(np.float32)


# ── After-analysis ────────────────────────────────────────────────────────────

def measure_after(audio: np.ndarray, sr: int) -> dict:
    from analyze import measure_loudness
    return measure_loudness(audio, sr)


# ── Master pipeline ───────────────────────────────────────────────────────────

def master_track(input_path: str, output_path: str, plan: dict) -> dict:
    """
    Apply full mastering chain based on plan dict.
    Returns dict with output metrics.
    """
    audio, sr = load_wav(input_path)

    # 1. Declip
    if plan.get("declip"):
        audio = declip(audio)

    # 2. Denoise
    if plan.get("denoise"):
        audio = denoise(audio, sr)

    # 3. EQ
    eq_bands = plan.get("eq") or []
    if eq_bands:
        audio = apply_eq(audio, sr, eq_bands)

    # 4. Compression
    comp = plan.get("compression")
    if comp:
        audio = apply_compression(
            audio, sr,
            threshold_db=float(comp.get("threshold", -20)),
            ratio=float(comp.get("ratio", 2.0)),
            attack_ms=float(comp.get("attack", 15)),
            release_ms=float(comp.get("release", 100)),
            expand=bool(comp.get("expand", False)),
        )

    # 5. Transient shaping
    if plan.get("transient_shape"):
        audio = apply_transient_shape(audio, sr)

    # 6. De-ess
    if plan.get("deess"):
        audio = apply_deess(audio, sr)

    # 7. Stereo: mono below hz
    mono_hz = plan.get("mono_below_hz")
    if mono_hz and mono_hz > 0:
        audio = apply_mono_below_hz(audio, sr, float(mono_hz))

    # 8. Stereo width
    sw = plan.get("stereo_width")
    if sw is not None:
        audio = apply_stereo_width(audio, float(sw))

    # 9. HF enhancement
    hfg = plan.get("hf_gain")
    if hfg and abs(float(hfg)) > 0.01:
        audio = apply_hf_gain(audio, sr, float(hfg))

    # 10. LUFS normalise (double-pass)
    target_lufs = float(plan.get("target_lufs", -14.0))
    audio = lufs_normalise(audio, sr, target_lufs)

    # 11. True-peak limit
    limiter = plan.get("limiter") or {}
    ceiling = float(limiter.get("ceiling", -1.0))
    rel     = float(limiter.get("release", 50.0))
    audio = true_peak_limit(audio, sr, ceiling, rel)

    # 12. Final LUFS correction pass (limiter may have reduced gain)
    audio = lufs_normalise(audio, sr, target_lufs, max_gain_db=3.0)

    # Save
    save_wav(output_path, audio, sr)

    # Measure final
    after = measure_after(audio, sr)

    return {
        "output_wav": output_path,
        "lufs_final": after["lufs"],
        "true_peak_final": after["true_peak_db"],
        "dr_final": after["dr"],
        "lra_final": after["lra"],
        "analysis_after": after,
    }
