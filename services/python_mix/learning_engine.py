"""
Learning engine: analyse high-rated sessions and update LearnedRules.
Called by UpdateLearning stored procedure trigger via /learn endpoint.
"""
import json
import numpy as np
import pyodbc
from db import get_connection, save_learned_rule, get_connection


def analyse_patterns(genre: str) -> list[dict]:
    """Find parameter patterns correlated with ratings >= 4 for a genre."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        """
        SELECT pi.ParametersJson, uf.Rating
        FROM ProcessingIterations pi
        JOIN MixSessions ms ON ms.Id = pi.SessionId
        JOIN UserFeedback uf ON uf.SessionId = ms.Id
        WHERE ms.Genre = ? AND uf.Rating >= 4 AND pi.IterationType = 'master'
        ORDER BY pi.IterationNumber DESC
        """,
        genre
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return []

    # Aggregate numeric parameters across sessions
    param_values: dict[str, list[float]] = {}
    ratings = []

    for params_json, rating in rows:
        ratings.append(rating)
        if not params_json:
            continue
        try:
            params = json.loads(params_json)
        except Exception:
            continue
        for k, v in _flatten(params).items():
            try:
                param_values.setdefault(k, []).append(float(v))
            except (TypeError, ValueError):
                pass

    patterns = []
    for param, values in param_values.items():
        if len(values) < 3:
            continue
        mean  = float(np.mean(values))
        std   = float(np.std(values))
        conf  = min(1.0, len(values) / 20)
        patterns.append({
            "parameter":   param,
            "value":       str(round(mean, 3)),
            "std":         round(std, 3),
            "confidence":  round(conf, 3),
            "sample_count": len(values),
        })

    return patterns


def update_learned_rules(genre: str) -> int:
    """Recalculate and persist LearnedRules for a genre. Returns count updated."""
    patterns = analyse_patterns(genre)
    count = 0
    for p in patterns:
        save_learned_rule(
            genre       = genre,
            parameter   = p["parameter"],
            value       = p["value"],
            unit        = None,
            confidence  = p["confidence"],
            sample_count = p["sample_count"],
        )
        count += 1

    if count >= 5:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("EXEC RecalculateLearnedRules @Genre = ?", genre)
        conn.commit()
        conn.close()

    return count


def _flatten(d: dict, prefix: str = "") -> dict:
    """Flatten nested dict to dot-notation keys."""
    out = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        elif isinstance(v, (int, float)):
            out[key] = v
    return out
