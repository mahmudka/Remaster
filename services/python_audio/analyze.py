"""
Full audio analysis: loudness metrics + 12 AI-artifact tags detection.
"""

import json
import warnings
import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from scipy import signal
from scipy.fft import rfft, rfftfreq

warnings.filterwarnings("ignore")


# ── Load ──────────────────────────────────────────────────────────────────────

def load_wav(path: str) -> tuple[np.ndarray, int]:
    data, sr = sf.read(path, dtype="float32", always_2d=True)
    return data, sr


def to_mono(audio: np.ndarray) -> np.ndarray:
    return audio.mean(axis=1) if audio.ndim == 2 else audio


# ── Loudness metrics ──────────────────────────────────────────────────────────

def measure_loudness(audio: np.ndarray, sr: int) -> dict:
    meter = pyln.Meter(sr)
    mono = to_mono(audio)

    # pyloudnorm expects float64 for lufs
    mono64 = mono.astype(np.float64)
    lufs = meter.integrated_loudness(mono64)

    # True peak (upsample 4x, find max)
    up = signal.resample_poly(mono, 4, 1)
    true_peak_linear = max(abs(up).max(), 1e-12)
    true_peak_db = float(20 * np.log10(true_peak_linear))

    # Dynamic Range (simplified): difference between 95th and 10th percentile
    rms_frames = _rms_frames(mono, sr)
    dr = float(np.percentile(rms_frames, 95) - np.percentile(rms_frames, 10)) if len(rms_frames) > 10 else 0.0

    # Loudness Range (LRA): difference between high and low loud percentiles
    lra = float(_loudness_range(mono64, sr))

    return {
        "lufs": float(lufs) if np.isfinite(lufs) else -70.0,
        "true_peak_db": true_peak_db,
        "dr": dr,
        "lra": lra,
    }


def _rms_frames(mono: np.ndarray, sr: int, frame_ms: int = 300) -> np.ndarray:
    frame = int(sr * frame_ms / 1000)
    n_frames = len(mono) // frame
    if n_frames < 2:
        return np.array([0.0])
    frames = mono[: n_frames * frame].reshape(n_frames, frame)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    rms_db = 20 * np.log10(np.maximum(rms, 1e-9))
    return rms_db


def _loudness_range(mono: np.ndarray, sr: int) -> float:
    meter = pyln.Meter(sr)
    try:
        # measure in 3s blocks
        block = int(sr * 3)
        if len(mono) < block:
            return 0.0
        n = len(mono) // block
        luf_vals = []
        for i in range(n):
            seg = mono[i * block: (i + 1) * block]
            v = meter.integrated_loudness(seg)
            if np.isfinite(v):
                luf_vals.append(v)
        if len(luf_vals) < 2:
            return 0.0
        arr = np.array(luf_vals)
        return float(np.percentile(arr, 95) - np.percentile(arr, 10))
    except Exception:
        return 0.0


# ── Spectral helpers ──────────────────────────────────────────────────────────

def _band_energy(fft_mag: np.ndarray, freqs: np.ndarray, lo: float, hi: float) -> float:
    mask = (freqs >= lo) & (freqs <= hi)
    if not mask.any():
        return 0.0
    return float(fft_mag[mask].mean())


def _spectral_centroid(fft_mag: np.ndarray, freqs: np.ndarray) -> float:
    total = fft_mag.sum()
    if total < 1e-12:
        return 0.0
    return float((fft_mag * freqs).sum() / total)


def compute_fft(mono: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    # Use middle 3s of audio for representative FFT
    mid = len(mono) // 2
    seg_len = min(sr * 3, len(mono))
    seg = mono[mid - seg_len // 2: mid + seg_len // 2]
    window = np.hanning(len(seg))
    fft_raw = np.abs(rfft(seg * window))
    freqs = rfftfreq(len(seg), 1.0 / sr)
    # Convert to dB, normalize
    fft_db = 20 * np.log10(np.maximum(fft_raw / (len(seg) / 2), 1e-12))
    return fft_db, freqs


# ── BPM / Key ─────────────────────────────────────────────────────────────────

def detect_bpm_key(audio: np.ndarray, sr: int) -> tuple[float, str]:
    try:
        import librosa
        mono_lr = librosa.to_mono(audio.T if audio.ndim == 2 else audio)
        tempo, _ = librosa.beat.beat_track(y=mono_lr.astype(np.float32), sr=sr)
        bpm = float(tempo[0]) if hasattr(tempo, "__len__") else float(tempo)

        chroma = librosa.feature.chroma_cqt(y=mono_lr.astype(np.float32), sr=sr)
        key_idx = int(chroma.mean(axis=1).argmax())
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        key = note_names[key_idx]
        return bpm, key
    except Exception:
        return 0.0, "unknown"


def detect_genre_hint(bpm: float, dr: float, lufs: float) -> str:
    if bpm < 1:
        return "unknown"
    if bpm >= 130 and dr < 8:
        return "edm"
    if 60 <= bpm <= 100 and dr >= 10:
        return "acoustic"
    if 90 <= bpm <= 130:
        return "pop"
    if bpm > 140:
        return "drum_and_bass"
    return "unknown"


# ── 12 AI-artifact detectors ──────────────────────────────────────────────────

def detect_metallic_resonance(fft_db: np.ndarray, freqs: np.ndarray) -> bool:
    # Narrow peaks in 2-5kHz: high variance relative to neighbors
    mask = (freqs >= 2000) & (freqs <= 5000)
    if not mask.any():
        return False
    band = fft_db[mask]
    # If std deviation is high, there are sharp resonant peaks
    return float(band.std()) > 8.0


def detect_muddy_lowmid(fft_db: np.ndarray, freqs: np.ndarray) -> bool:
    # Excess energy 200-400Hz vs 400-800Hz baseline
    energy_200_400 = _band_energy(fft_db, freqs, 200, 400)
    energy_400_800 = _band_energy(fft_db, freqs, 400, 800)
    energy_1k_4k   = _band_energy(fft_db, freqs, 1000, 4000)
    # Muddy if 200-400 is significantly louder than the clarity band
    return (energy_200_400 - energy_1k_4k) > 6.0 or (energy_200_400 - energy_400_800) > 4.0


def detect_missing_transients(mono: np.ndarray, sr: int) -> bool:
    # Measure onset strength — low onset density = missing transients
    try:
        import librosa
        onset_env = librosa.onset.onset_strength(y=mono.astype(np.float32), sr=sr)
        # Normalised peak rate
        peaks = (onset_env > onset_env.mean() + onset_env.std()).sum()
        duration_s = len(mono) / sr
        onset_rate = peaks / max(duration_s, 1)
        return onset_rate < 0.3  # fewer than 0.3 onsets/sec = suspicious
    except Exception:
        return False


def detect_over_compressed(dr: float, lra: float) -> bool:
    # Very low dynamic range indicates heavy compression
    return dr < 6.0 or lra < 3.0


def detect_artificial_stereo(audio: np.ndarray) -> bool:
    if audio.ndim < 2 or audio.shape[1] < 2:
        return False
    L = audio[:, 0].astype(np.float64)
    R = audio[:, 1].astype(np.float64)
    # Correlation between L and R
    if L.std() < 1e-9 or R.std() < 1e-9:
        return False
    corr = float(np.corrcoef(L, R)[0, 1])
    # Very high (>0.98, essentially mono) or very low (<-0.3, unnatural widening)
    return corr > 0.98 or corr < -0.3


def detect_phase_issues(audio: np.ndarray) -> bool:
    if audio.ndim < 2 or audio.shape[1] < 2:
        return False
    L = audio[:, 0].astype(np.float64)
    R = audio[:, 1].astype(np.float64)
    mid  = (L + R) / 2
    side = (L - R) / 2
    mid_rms  = float(np.sqrt((mid ** 2).mean()))
    side_rms = float(np.sqrt((side ** 2).mean()))
    if mid_rms < 1e-9:
        return False
    # If side energy greatly exceeds mid, phase issues likely
    ratio = side_rms / mid_rms
    return ratio > 0.9


def detect_ai_noise(mono: np.ndarray, sr: int) -> bool:
    try:
        # Check noise floor in the last 500ms of silence-like section
        # Find quietest 1s segment
        block = int(sr * 1.0)
        n_blocks = len(mono) // block
        if n_blocks < 2:
            return False
        rms_blocks = [float(np.sqrt((mono[i*block:(i+1)*block]**2).mean())) for i in range(n_blocks)]
        noise_floor_rms = min(rms_blocks)
        noise_floor_db = float(20 * np.log10(max(noise_floor_rms, 1e-12)))
        # AI-generated tracks often have elevated noise floor (-50 to -40 dBFS)
        return noise_floor_db > -55.0
    except Exception:
        return False


def detect_sibilance(fft_db: np.ndarray, freqs: np.ndarray) -> bool:
    # Excess energy 5-8kHz vs 3-5kHz
    energy_5_8 = _band_energy(fft_db, freqs, 5000, 8000)
    energy_3_5 = _band_energy(fft_db, freqs, 3000, 5000)
    return (energy_5_8 - energy_3_5) > 5.0


def detect_sub_issues(fft_db: np.ndarray, freqs: np.ndarray, lufs: float) -> bool:
    # Excessive sub-bass 20-60Hz that may be causing loudness issues
    energy_sub  = _band_energy(fft_db, freqs, 20, 60)
    energy_bass = _band_energy(fft_db, freqs, 60, 200)
    energy_mid  = _band_energy(fft_db, freqs, 200, 2000)
    return (energy_sub - energy_mid) > 8.0 or (energy_sub - energy_bass) > 6.0


def detect_true_peak_clip(true_peak_db: float) -> bool:
    return true_peak_db > -0.5


def detect_spectral_smearing(fft_db: np.ndarray, freqs: np.ndarray) -> bool:
    # Lack of high-frequency content above 12kHz
    energy_air    = _band_energy(fft_db, freqs, 12000, 20000)
    energy_pres   = _band_energy(fft_db, freqs, 5000, 12000)
    # Heavy smoothing (absence of air) is characteristic of AI generation
    return (energy_pres - energy_air) > 25.0


def detect_loudness_mismatch(lufs: float, target: float = -14.0) -> bool:
    return abs(lufs - target) > 3.0


# ── Main entry ────────────────────────────────────────────────────────────────

def analyze_file(path: str, target_lufs: float = -14.0) -> dict:
    audio, sr = load_wav(path)
    mono = to_mono(audio)

    loud = measure_loudness(audio, sr)
    lufs       = loud["lufs"]
    true_peak  = loud["true_peak_db"]
    dr         = loud["dr"]
    lra        = loud["lra"]

    fft_db, freqs = compute_fft(mono, sr)
    bpm, key = detect_bpm_key(audio, sr)
    genre = detect_genre_hint(bpm, dr, lufs)

    problems: list[str] = []

    if detect_metallic_resonance(fft_db, freqs):
        problems.append("metallic_resonance")

    if detect_muddy_lowmid(fft_db, freqs):
        problems.append("muddy_lowmid")

    if detect_missing_transients(mono, sr):
        problems.append("missing_transients")

    if detect_over_compressed(dr, lra):
        problems.append("over_compressed")

    if detect_artificial_stereo(audio):
        problems.append("artificial_stereo")

    if detect_phase_issues(audio):
        problems.append("phase_issues")

    if detect_ai_noise(mono, sr):
        problems.append("ai_noise")

    if detect_sibilance(fft_db, freqs):
        problems.append("sibilance")

    if detect_sub_issues(fft_db, freqs, lufs):
        problems.append("sub_issues")

    if detect_true_peak_clip(true_peak):
        problems.append("true_peak_clip")

    if detect_spectral_smearing(fft_db, freqs):
        problems.append("spectral_smearing")

    if detect_loudness_mismatch(lufs, target_lufs):
        problems.append("loudness_mismatch")

    analysis = {
        "lufs": lufs,
        "true_peak": true_peak,
        "dr": dr,
        "lra": lra,
        "bpm": bpm,
        "key": key,
        "genre_hint": genre,
        "sample_rate": sr,
        "duration_s": round(len(mono) / sr, 2),
        "channels": audio.shape[1] if audio.ndim == 2 else 1,
        "problems": problems,
    }

    return analysis
