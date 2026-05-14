import os
import json
import tempfile
import shutil
from contextlib import asynccontextmanager
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from mix_engine import mix_stems
from master_engine import master_track, measure_lufs
from learning_engine import update_learned_rules
from book_parser import parse_pdf
from knowledge_service import extract_rules_from_chunk, generate_mix_plan
from audio_io import read_audio

try:
    from db import (get_session_id, save_iteration, save_similarity,
                    update_session_status, get_best_parameters, get_connection)
    get_connection().close()  # probe: fails fast if driver is broken
    DB_OK = True
except Exception as e:
    DB_OK = False
    _DB_ERR = str(e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[startup] db={DB_OK}")
    yield


app = FastAPI(title="AudioPipeline Mix Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "port": 8002, "db": DB_OK}


# ── Mix ───────────────────────────────────────────────────────────────────────

@app.post("/mix")
async def mix(
    stems_json:  str = Form(...),   # {"vocals":"/path","bass":"/path",...}
    plan_json:   str = Form(...),   # MixPlan JSON from KnowledgeAgent
    output_dir:  str = Form(...),
    job_id:      str = Form(...),
    iteration:   int = Form(1),
):
    stems = json.loads(stems_json)
    plan  = json.loads(plan_json)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"mix_iter{iteration}.wav")

    try:
        mix_stems(stems, plan, output_path)
        lufs_i, lufs_tp = measure_lufs(*read_audio(output_path))

        if DB_OK:
            sid = get_session_id(job_id)
            if sid:
                save_iteration(sid, "mix", iteration, plan, output_path, lufs_i, lufs_tp)
                update_session_status(job_id, "Mixed")

        return {
            "job_id":          job_id,
            "iteration":       iteration,
            "output":          output_path,
            "lufs_integrated": lufs_i,
            "lufs_true_peak":  lufs_tp,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Master ────────────────────────────────────────────────────────────────────

@app.post("/master")
async def master(
    input_path:   str   = Form(...),
    output_dir:   str   = Form(...),
    job_id:       str   = Form(...),
    iteration:    int   = Form(1),
    target_lufs:  float = Form(-14.0),
):
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"master_iter{iteration}.wav")

    try:
        result = master_track(input_path, output_path, target_lufs)

        if DB_OK:
            sid = get_session_id(job_id)
            if sid:
                save_iteration(sid, "master", iteration, {"target_lufs": target_lufs},
                               output_path, result["lufs_integrated"], result["lufs_true_peak"])
                if iteration >= 3 or abs(result["lufs_integrated"] - target_lufs) < 0.5:
                    update_session_status(job_id, "Done")

        return {"job_id": job_id, **result}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Learning ──────────────────────────────────────────────────────────────────

@app.post("/learn")
async def learn(
    genre:      str = Form(...),
    session_id: int = Form(...),
):
    try:
        count = update_learned_rules(genre)
        return {"genre": genre, "rules_updated": count}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Book parsing ──────────────────────────────────────────────────────────────

@app.post("/parse_book")
async def parse_book(
    file:       UploadFile = File(...),
    book_id:    int        = Form(...),
    book_title: str        = Form(...),
):
    tmp = tempfile.mktemp(suffix=".pdf")
    try:
        with open(tmp, "wb") as f:
            shutil.copyfileobj(file.file, f)
        chunks = parse_pdf(tmp)
        return {"book_id": book_id, "chunks": len(chunks), "preview": chunks[:2]}
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ── Knowledge / Mix plan ──────────────────────────────────────────────────────

@app.post("/mix_plan")
async def mix_plan(
    track_profile_json: str = Form(...),
    genre:              str = Form(...),
):
    profile = json.loads(track_profile_json)
    try:
        plan = generate_mix_plan(profile, genre)
        return {"genre": genre, "plan": plan}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── JSON body endpoints (used by .NET agents) ─────────────────────────────────

class MixJsonRequest(BaseModel):
    vocals: str | None = None
    bass: str | None = None
    drums: str | None = None
    instruments: str | None = None
    mix_plan: dict = {}
    output_path: str
    job_id: str = ""
    reference_file: str | None = None
    iteration: int = 1

@app.post("/mix_json")
async def mix_json(req: MixJsonRequest):
    stems = {}
    for stem in ("vocals", "bass", "drums", "instruments"):
        path = getattr(req, stem)
        if path:
            stems[stem] = path
    os.makedirs(req.output_path, exist_ok=True)
    output_wav = os.path.join(req.output_path, f"mix_iter{req.iteration}.wav")
    try:
        mix_stems(stems, req.mix_plan, output_wav)
        lufs_i, lufs_tp = measure_lufs(*read_audio(output_wav))
    except Exception as e:
        raise HTTPException(500, str(e))
    if DB_OK and req.job_id:
        try:
            sid = get_session_id(req.job_id)
            if sid:
                save_iteration(sid, "mix", req.iteration, req.mix_plan, output_wav, lufs_i, lufs_tp)
                update_session_status(req.job_id, "Mixed")
        except Exception:
            pass
    return {"mix_wav": output_wav, "lufs_integrated": lufs_i, "lufs_true_peak": lufs_tp}


class MasterJsonRequest(BaseModel):
    mix_wav: str
    output_path: str
    job_id: str = ""
    iteration: int = 1
    target_lufs: float = -14.0

@app.post("/master_json")
async def master_json(req: MasterJsonRequest):
    os.makedirs(req.output_path, exist_ok=True)
    output_wav = os.path.join(req.output_path, "master.wav")
    try:
        result = master_track(req.mix_wav, output_wav, req.target_lufs)
    except Exception as e:
        raise HTTPException(500, str(e))
    if DB_OK and req.job_id:
        try:
            sid = get_session_id(req.job_id)
            if sid:
                save_iteration(sid, "master", req.iteration, {"target_lufs": req.target_lufs},
                               output_wav, result["lufs_integrated"], result["lufs_true_peak"])
                update_session_status(req.job_id, "Done")
        except Exception:
            pass
    return {"master_wav": output_wav, "master_mp3": None,
            "lufs_integrated": result["lufs_integrated"], "lufs_true_peak": result["lufs_true_peak"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=False)
