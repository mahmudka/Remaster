"""
Local mastering plan generator.
Builds a MasteringPlan from problem tags using KnowledgeBase rules + learned rules.
No external API calls.
"""

from __future__ import annotations
import json


# ── Default DSP parameters by problem tag ─────────────────────────────────────

_TAG_DEFAULTS: dict[str, dict] = {
    "metallic_resonance": {
        "eq": [
            {"frequency": 3500, "gain": -3.0, "q": 2.5, "type": "peak"},
            {"frequency": 5000, "gain": -2.0, "q": 2.0, "type": "peak"},
        ],
    },
    "muddy_lowmid": {
        "eq": [
            {"frequency": 300, "gain": -4.0, "q": 1.5, "type": "peak"},
            {"frequency": 200, "gain": -2.0, "q": 1.0, "type": "peak"},
        ],
    },
    "missing_transients": {
        "transient_shape": True,
        "compression": {"threshold": -20.0, "ratio": 1.5, "attack": 30.0, "release": 80.0},
    },
    "over_compressed": {
        "compression": {"threshold": -18.0, "ratio": 1.3, "attack": 40.0, "release": 120.0, "expand": True},
    },
    "artificial_stereo": {
        "stereo_width": 0.7,
    },
    "phase_issues": {
        "stereo_width": 0.8,
    },
    "ai_noise": {
        "denoise": True,
    },
    "sibilance": {
        "deess": True,
        "eq": [
            {"frequency": 6500, "gain": -2.5, "q": 1.5, "type": "peak"},
        ],
    },
    "sub_issues": {
        "mono_below_hz": 80.0,
        "eq": [
            {"frequency": 40, "gain": -4.0, "q": 0.8, "type": "highpass"},
        ],
    },
    "true_peak_clip": {
        "declip": True,
        "limiter": {"ceiling": -1.0, "release": 50.0},
    },
    "spectral_smearing": {
        "hf_gain": 1.5,
        "eq": [
            {"frequency": 14000, "gain": 1.5, "q": 0.7, "type": "shelf"},
            {"frequency": 10000, "gain": 1.0, "q": 0.9, "type": "peak"},
        ],
    },
    "loudness_mismatch": {
        # Handled by normalization, no EQ change needed
    },
}


def _merge_eq(existing: list[dict], new_bands: list[dict]) -> list[dict]:
    """Merge EQ bands, avoiding duplicate frequencies within 200 Hz."""
    result = list(existing)
    for band in new_bands:
        freq = band["frequency"]
        if not any(abs(b["frequency"] - freq) < 200 for b in result):
            result.append(band)
    return result


def build_plan(
    tags: list[str],
    genre: str,
    target_lufs: float,
    db_rules: list[dict] | None = None,
    learned_rules: list[dict] | None = None,
) -> dict:
    """
    Build a mastering plan dict from problem tags.
    DB rules and learned rules fine-tune the defaults.
    """
    eq_bands: list[dict] = []
    compression: dict | None = None
    limiter = {"ceiling": -1.0, "release": 50.0}
    stereo_width: float | None = None
    denoise = False
    declip = False
    transient_shape = False
    deess = False
    mono_below_hz: float | None = None
    hf_gain: float | None = None
    sources: list[str] = []

    applied_tags = list(tags)

    # Apply defaults from tag map
    for tag in tags:
        defaults = _TAG_DEFAULTS.get(tag, {})
        if "eq" in defaults:
            eq_bands = _merge_eq(eq_bands, defaults["eq"])
        if "compression" in defaults:
            if compression is None:
                compression = dict(defaults["compression"])
            else:
                # Take more conservative values
                c = defaults["compression"]
                compression["threshold"] = max(compression["threshold"], c["threshold"])
                compression["ratio"] = min(compression["ratio"], c["ratio"])
        if "limiter" in defaults:
            limiter = defaults["limiter"]
        if "stereo_width" in defaults:
            v = defaults["stereo_width"]
            stereo_width = v if stereo_width is None else (stereo_width + v) / 2
        if defaults.get("denoise"):
            denoise = True
        if defaults.get("declip"):
            declip = True
        if defaults.get("transient_shape"):
            transient_shape = True
        if defaults.get("deess"):
            deess = True
        if "mono_below_hz" in defaults:
            mono_below_hz = defaults["mono_below_hz"]
        if "hf_gain" in defaults:
            hf_gain = defaults["hf_gain"]

    # Override / refine from DB knowledge rules
    if db_rules:
        for rule in db_rules:
            param = (rule.get("parameter") or "").lower()
            try:
                val = float(rule.get("value") or 0)
            except (ValueError, TypeError):
                val = 0.0
            unit = (rule.get("unit") or "").lower()
            rationale = rule.get("rationale") or ""

            if "eq" in param and "hz" in unit and val > 0:
                eq_bands = _merge_eq(eq_bands, [{
                    "frequency": val,
                    "gain": -2.0,
                    "q": 1.5,
                    "type": "peak",
                }])
                sources.append(f"KB: {rule.get('parameter')}")
            elif "threshold" in param and compression is not None:
                compression["threshold"] = val
            elif "ratio" in param and compression is not None:
                compression["ratio"] = val
            elif "target_lufs" in param or "lufs" in param:
                if val < 0:
                    target_lufs = val
            elif "ceiling" in param or "limiter" in param:
                limiter["ceiling"] = val if val <= 0 else -abs(val)

    # Apply learned rules (user feedback → higher confidence adjustments)
    if learned_rules:
        for rule in learned_rules:
            param = (rule.get("parameter") or "").lower()
            try:
                val = float(rule.get("value") or 0)
            except (ValueError, TypeError):
                val = 0.0
            if rule.get("confidence", 0) < 0.55:
                continue
            if "target_lufs" in param and val < 0:
                target_lufs = val
                sources.append(f"Learned({rule.get('genre')}): target_lufs={val}")
            elif "stereo_width" in param and 0 < val <= 1.5:
                stereo_width = val

    # Safety: if no compression set but we have over_compressed or missing_transients, add light default
    if compression is None and ("over_compressed" in tags or "missing_transients" in tags):
        compression = {"threshold": -20.0, "ratio": 2.0, "attack": 15.0, "release": 100.0, "expand": False}

    return {
        "eq": eq_bands,
        "compression": compression,
        "limiter": limiter,
        "target_lufs": target_lufs,
        "stereo_width": stereo_width,
        "denoise": denoise,
        "declip": declip,
        "transient_shape": transient_shape,
        "deess": deess,
        "mono_below_hz": mono_below_hz,
        "hf_gain": hf_gain,
        "sources": sources,
        "applied_tags": applied_tags,
    }
