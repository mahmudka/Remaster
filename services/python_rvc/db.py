import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=AudioPipeline;"
    "Trusted_Connection=yes;"
)


def get_connection():
    return pyodbc.connect(CONN_STR)


def list_models() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT Id, Name, ModelPath, IndexPath, Description, IsDefault, CreatedAt "
        "FROM VoiceModels ORDER BY IsDefault DESC, Name"
    )
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def get_model(model_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM VoiceModels WHERE Id=?", model_id)
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def add_model(name: str, model_path: str, index_path: str | None,
              description: str | None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO VoiceModels (Name, ModelPath, IndexPath, Description) "
        "OUTPUT INSERTED.Id VALUES (?,?,?,?)",
        name, model_path, index_path, description
    )
    row = cur.fetchone()
    conn.commit()
    conn.close()
    return row[0]


def delete_model(model_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM VoiceModels WHERE Id=?", model_id)
    conn.commit()
    conn.close()


def set_default(model_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE VoiceModels SET IsDefault=0")
    cur.execute("UPDATE VoiceModels SET IsDefault=1 WHERE Id=?", model_id)
    conn.commit()
    conn.close()
