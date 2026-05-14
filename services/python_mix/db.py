import json
import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=AudioPipeline;"
    "Trusted_Connection=yes;"
)


def get_connection():
    return pyodbc.connect(CONN_STR)


def get_best_parameters(genre: str) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("EXEC GetBestParameters @Genre = ?", genre)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    return rows


def save_iteration(session_id: int, iter_type: str, iter_num: int,
                   params: dict, output_file: str,
                   lufs_i: float | None = None, lufs_tp: float | None = None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ProcessingIterations
            (SessionId, IterationType, IterationNumber, ParametersJson, OutputFile,
             LufsIntegrated, LufsTruePeak)
        OUTPUT INSERTED.Id
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        session_id, iter_type, iter_num,
        json.dumps(params), output_file, lufs_i, lufs_tp
    )
    row = cur.fetchone()
    conn.commit()
    conn.close()
    return row[0] if row else -1


def save_similarity(session_id: int, iteration_id: int | None,
                    score: float, freq_diff: dict, dyn_diff: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO SimilarityReports
            (SessionId, IterationId, SimilarityScore, FrequencyDiffJson, DynamicsDiffJson)
        VALUES (?, ?, ?, ?, ?)
        """,
        session_id, iteration_id, score,
        json.dumps(freq_diff), json.dumps(dyn_diff)
    )
    conn.commit()
    conn.close()


def save_learned_rule(genre: str, parameter: str, value: str,
                      unit: str | None, confidence: float, sample_count: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT Id FROM LearnedRules WHERE Genre=? AND Parameter=?",
        genre, parameter
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            "UPDATE LearnedRules SET Value=?, Confidence=?, SampleCount=?, UpdatedAt=GETDATE() WHERE Id=?",
            value, confidence, sample_count, row[0]
        )
    else:
        cur.execute(
            "INSERT INTO LearnedRules (Genre, Parameter, Value, Unit, Confidence, SampleCount) VALUES (?,?,?,?,?,?)",
            genre, parameter, value, unit, confidence, sample_count
        )
    conn.commit()
    conn.close()


def get_session_id(job_id: str) -> int | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT Id FROM MixSessions WHERE JobId=?", job_id)
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def update_session_status(job_id: str, status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE MixSessions SET Status=?, CompletedAt=CASE WHEN ?='Done' THEN GETDATE() ELSE NULL END WHERE JobId=?",
        status, status, job_id
    )
    conn.commit()
    conn.close()
