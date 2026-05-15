import os
import json
import pyodbc

_CONN_STR = (
    os.environ.get("DB_CONNECTION_STRING")
    or "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=AudioPipeline;Trusted_Connection=yes;"
)


def get_connection():
    return pyodbc.connect(_CONN_STR, timeout=10)


def get_session_id(job_id: str) -> int | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT Id FROM MixSessions WHERE JobId = ?", job_id).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def update_session_status(job_id: str, status: str, **fields):
    conn = get_connection()
    try:
        if fields:
            set_parts = ", ".join(f"{k}=?" for k in fields)
            values = list(fields.values()) + [status, job_id]
            conn.execute(
                f"UPDATE MixSessions SET {set_parts}, Status=? WHERE JobId=?", *values
            )
        else:
            conn.execute("UPDATE MixSessions SET Status=? WHERE JobId=?", status, job_id)
        conn.commit()
    finally:
        conn.close()


def get_rules_by_tags(tags: list[str], genre: str | None = None, limit: int = 60) -> list[dict]:
    if not tags:
        return []
    conn = get_connection()
    try:
        like_params = [f"%{t}%" for t in tags]
        tag_conditions = " OR ".join("Tags LIKE ?" for _ in tags)
        genre_clause = ""
        extra_params: list = []
        if genre:
            genre_clause = " AND (Genre IS NULL OR Genre = ? OR Genre = 'all')"
            extra_params.append(genre)
        query = f"""
            SELECT TOP {limit} Parameter, Value, Unit, Rationale, Tags
            FROM KnowledgeBase
            WHERE Tags IS NOT NULL AND ({tag_conditions})
            {genre_clause}
            ORDER BY Confidence DESC
        """
        rows = conn.execute(query, *like_params, *extra_params).fetchall()
        return [
            {"parameter": r[0], "value": r[1], "unit": r[2],
             "rationale": r[3], "tags": r[4]}
            for r in rows
        ]
    finally:
        conn.close()


def get_learned_rules(genre: str | None = None) -> list[dict]:
    conn = get_connection()
    try:
        if genre:
            rows = conn.execute(
                "SELECT Genre, Parameter, Value, Confidence FROM LearnedRules WHERE Genre=? ORDER BY Confidence DESC",
                genre
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT Genre, Parameter, Value, Confidence FROM LearnedRules ORDER BY Confidence DESC"
            ).fetchall()
        return [{"genre": r[0], "parameter": r[1], "value": r[2], "confidence": float(r[3])} for r in rows]
    finally:
        conn.close()


def upsert_learned_rule(genre: str, parameter: str, value: str, delta: float = 0.05):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT Id, Confidence FROM LearnedRules WHERE Genre=? AND Parameter=?",
            genre, parameter
        ).fetchone()
        if row:
            new_conf = min(1.0, float(row[1]) + delta)
            conn.execute(
                "UPDATE LearnedRules SET Value=?, Confidence=?, UpdatedAt=GETUTCDATE() WHERE Id=?",
                value, new_conf, row[0]
            )
        else:
            conn.execute(
                "INSERT INTO LearnedRules (Genre, Parameter, Value, Confidence, UpdatedAt) VALUES (?,?,?,?,GETUTCDATE())",
                genre, parameter, value, 0.5 + delta
            )
        conn.commit()
    finally:
        conn.close()


def get_sessions_for_learning(genre: str, min_rating: int = 4) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT ms.Id, ms.PlanJson, ms.AnalysisBeforeJson, uf.Rating, uf.FeedbackTagsJson
            FROM MixSessions ms
            JOIN UserFeedback uf ON uf.SessionId = ms.Id
            WHERE ms.Genre = ? AND uf.Rating >= ?
            ORDER BY uf.CreatedAt DESC
        """, genre, min_rating).fetchall()
        return [
            {"id": r[0], "plan": r[1], "analysis": r[2], "rating": r[3], "tags": r[4]}
            for r in rows
        ]
    finally:
        conn.close()
