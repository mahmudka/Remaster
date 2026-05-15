"""
Learning engine: extracts patterns from high-rated sessions and updates LearnedRules.
"""

import json


def update_learned_rules(genre: str) -> int:
    try:
        from db import get_sessions_for_learning, upsert_learned_rule
    except ImportError:
        return 0

    sessions = get_sessions_for_learning(genre, min_rating=4)
    if not sessions:
        return 0

    # Accumulate parameter values from high-rated sessions
    param_values: dict[str, list[float]] = {}

    for s in sessions:
        plan_json = s.get("plan") or ""
        if not plan_json:
            continue
        try:
            plan = json.loads(plan_json)
        except Exception:
            continue

        # target_lufs
        tl = plan.get("target_lufs")
        if tl is not None:
            try:
                param_values.setdefault("target_lufs", []).append(float(tl))
            except (ValueError, TypeError):
                pass

        # stereo_width
        sw = plan.get("stereo_width")
        if sw is not None:
            try:
                param_values.setdefault("stereo_width", []).append(float(sw))
            except (ValueError, TypeError):
                pass

        # compression ratio
        comp = plan.get("compression") or {}
        ratio = comp.get("ratio")
        if ratio is not None:
            try:
                param_values.setdefault("compression_ratio", []).append(float(ratio))
            except (ValueError, TypeError):
                pass

    updated = 0
    for param, values in param_values.items():
        if not values:
            continue
        avg = sum(values) / len(values)
        confidence_delta = min(0.05 * len(values), 0.2)
        upsert_learned_rule(genre, param, str(round(avg, 4)), delta=confidence_delta)
        updated += 1

    return updated
