import os
import json
import tempfile
import shutil
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from analyze import analyze_file
from plan import build_plan
from mastering import master_track
from learning import update_learned_rules

try:
    from db import get_connection, update_session_status, get_rules_by_tags, get_learned_rules
    get_connection().close()
    DB_OK = True
except Exception as _e:
    DB_OK = False
    _DB_ERR = str(_e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[startup] AudioPipeline Audio Service | db={DB_OK} | port=8001")
    yield


app = FastAPI(title="AudioPipeline Audio Service", version="2.0.0", lifespan=lifespan)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "port": 8001, "db": DB_OK}


# ── Analyse ───────────────────────────────────────────────────────────────────

@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    target_lufs: float = Form(-14.0),
    job_id: str = Form(""),
):
    suffix = os.path.splitext(file.filename or "upload")[1] or ".wav"
    tmp = tempfile.mktemp(suffix=suffix)
    try:
        with open(tmp, "wb") as f:
            shutil.copyfileobj(file.file, f)

        result = analyze_file(tmp, target_lufs=target_lufs)

        if DB_OK and job_id:
            try:
                update_session_status(
                    job_id, "Analyzed",
                    AnalysisBeforeJson=json.dumps(result),
                    Genre=result.get("genre_hint") or "unknown",
                    ProblemsDetected=json.dumps(result.get("problems", [])),
                )
            except Exception:
                pass

        return result
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ── Plan ──────────────────────────────────────────────────────────────────────

class PlanRequest(BaseModel):
    tags: list[str] = []
    genre: str = "unknown"
    target_lufs: float = -14.0
    job_id: str = ""


@app.post("/plan")
def plan(req: PlanRequest):
    db_rules: list[dict] = []
    learned: list[dict] = []

    if DB_OK and req.tags:
        try:
            db_rules = get_rules_by_tags(req.tags, req.genre)
        except Exception:
            pass
        try:
            learned = get_learned_rules(req.genre)
        except Exception:
            pass

    result = build_plan(
        tags=req.tags,
        genre=req.genre,
        target_lufs=req.target_lufs,
        db_rules=db_rules,
        learned_rules=learned,
    )

    if DB_OK and req.job_id:
        try:
            update_session_status(req.job_id, "Planned", PlanJson=json.dumps(result))
        except Exception:
            pass

    return result


# ── Master ────────────────────────────────────────────────────────────────────

class MasterRequest(BaseModel):
    input_path: str
    plan: dict
    output_path: str
    job_id: str = ""


@app.post("/master")
def master(req: MasterRequest):
    if not os.path.isfile(req.input_path):
        raise HTTPException(400, f"input_path not found: {req.input_path}")

    os.makedirs(os.path.dirname(req.output_path) or ".", exist_ok=True)

    try:
        result = master_track(req.input_path, req.output_path, req.plan)
    except Exception as e:
        raise HTTPException(500, str(e))

    analysis_after = result.get("analysis_after") or {}

    if DB_OK and req.job_id:
        try:
            update_session_status(
                req.job_id, "Done",
                AnalysisAfterJson=json.dumps(analysis_after),
            )
        except Exception:
            pass

    return {
        "output_wav":      result["output_wav"],
        "lufs_final":      result["lufs_final"],
        "true_peak_final": result["true_peak_final"],
        "dr_final":        result["dr_final"],
        "lra_final":       result["lra_final"],
        "analysis_after":  analysis_after,
        "report":          result,
    }


# ── Learn ─────────────────────────────────────────────────────────────────────

@app.post("/learn")
def learn(
    genre:      str = Form(...),
    session_id: int = Form(0),
):
    if not DB_OK:
        return {"genre": genre, "rules_updated": 0, "error": "db_unavailable"}
    try:
        count = update_learned_rules(genre)
        return {"genre": genre, "rules_updated": count}
    except Exception as e:
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
