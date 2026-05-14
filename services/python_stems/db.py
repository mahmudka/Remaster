import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=AudioPipeline;"
    "Trusted_Connection=yes;"
)

def get_connection():
    return pyodbc.connect(CONN_STR)

def save_session_analysis(job_id: str, bpm: float, key: str, genre: str,
                           freq_map: str, dynamics: str, stereo: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE MixSessions SET Bpm=?, [Key]=?, Genre=?, Status='Analyzed' WHERE JobId=?",
        bpm, key, genre, job_id
    )
    cur.execute(
        """
        INSERT INTO TrackDiagnosis (SessionId, FrequencyMapJson, DynamicsProfileJson, StereoProfileJson)
        SELECT Id, ?, ?, ? FROM MixSessions WHERE JobId=?
        """,
        freq_map, dynamics, stereo, job_id
    )
    conn.commit()
    conn.close()
