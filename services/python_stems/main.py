import os
import json
import tempfile
import shutil
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from pydantic import BaseModel
from analyze import analyze_track
from stems import separate_stems, DEMUCS_OK
from midi import transcribe_stems, BASIC_PITCH_OK

try:
    from db import save_session_analysis
    DB_OK = True
except Exception as e:
    DB_OK = False
    _DB_ERR = str(e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[startup] demucs={DEMUCS_OK}  basic-pitch={BASIC_PITCH_OK}  db={DB_OK}")
    yield


app = FastAPI(title="AudioPipeline Stems Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "port": 8001,
        "capabilities": {
            "analyze":    True,
            "stems":      DEMUCS_OK,
            "midi":       BASIC_PITCH_OK,
            "db":         DB_OK,
        }
    }


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    job_id: str = Form(...)
):
    tmp = tempfile.mktemp(suffix=os.path.splitext(file.filename or ".wav")[1])
    try:
        with open(tmp, "wb") as f:
            shutil.copyfileobj(file.file, f)

        result = analyze_track(tmp)

        if DB_OK:
            try:
                save_session_analysis(
                    job_id,
                    result["bpm"],
                    result["key"],
                    result["genre"],
                    result["frequency_map"],
                    result["dynamics_profile"],
                    result["stereo_profile"],
                )
            except Exception as e:
                result["db_warning"] = str(e)

        return result
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


@app.post("/stems")
async def stems(
    file: UploadFile = File(...),
    job_id: str = Form(...),
    output_dir: str = Form(...)
):
    if not DEMUCS_OK:
        raise HTTPException(503, "Demucs not available — torch/torchaudio install incomplete")

    tmp = tempfile.mktemp(suffix=os.path.splitext(file.filename or ".wav")[1])
    try:
        with open(tmp, "wb") as f:
            shutil.copyfileobj(file.file, f)
        stem_paths = separate_stems(tmp, output_dir)
        return {"job_id": job_id, "stems": stem_paths}
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


@app.post("/stems_local")
async def stems_local(
    input_path: str = Form(...),
    job_id: str = Form(...),
    output_dir: str = Form(...)
):
    """Separate stems from a server-local file path (no upload needed)."""
    if not os.path.exists(input_path):
        raise HTTPException(404, f"File not found: {input_path}")
    stem_paths = separate_stems(input_path, output_dir)
    return {"job_id": job_id, "stems": stem_paths}


@app.post("/midi")
async def midi(
    stems_json: str = Form(...),
    output_dir: str = Form(...),
    job_id: str = Form(...)
):
    """Transcribe stems to MIDI. stems_json: {"bass":"/path","drums":"/path",...}"""
    stems = json.loads(stems_json)
    midi_files = transcribe_stems(stems, output_dir)
    return {"job_id": job_id, "midi": midi_files}


# ── Local-path JSON endpoints (used by .NET agents) ───────────────────────────

class AnalyzeLocalRequest(BaseModel):
    file_path: str
    job_id: str = ""

@app.post("/analyze_local")
async def analyze_local(req: AnalyzeLocalRequest):
    if not os.path.exists(req.file_path):
        raise HTTPException(404, f"File not found: {req.file_path}")
    result = analyze_track(req.file_path)
    if DB_OK and req.job_id:
        try:
            save_session_analysis(req.job_id, result["bpm"], result["key"], result["genre"],
                                  result.get("frequency_map"), result.get("dynamics_profile"),
                                  result.get("stereo_profile"))
        except Exception as e:
            result["db_warning"] = str(e)
    return result


class StemsJsonRequest(BaseModel):
    file_path: str
    output_path: str
    job_id: str = ""

@app.post("/stems_json")
async def stems_json(req: StemsJsonRequest):
    if not os.path.exists(req.file_path):
        raise HTTPException(404, f"File not found: {req.file_path}")
    os.makedirs(req.output_path, exist_ok=True)
    stem_paths = separate_stems(req.file_path, req.output_path)
    return {"job_id": req.job_id, "vocals": stem_paths.get("vocals"),
            "bass": stem_paths.get("bass"), "drums": stem_paths.get("drums"),
            "instruments": stem_paths.get("instruments")}


class MidiJsonRequest(BaseModel):
    bass_stem: str | None = None
    drums_stem: str | None = None
    instruments_stem: str | None = None
    output_path: str
    job_id: str = ""

@app.post("/midi_json")
async def midi_json(req: MidiJsonRequest):
    stems = {}
    if req.bass_stem:        stems["bass"]        = req.bass_stem
    if req.drums_stem:       stems["drums"]       = req.drums_stem
    if req.instruments_stem: stems["instruments"] = req.instruments_stem
    os.makedirs(req.output_path, exist_ok=True)
    midi_files = transcribe_stems(stems, req.output_path)
    return {
        "job_id": req.job_id,
        "bass_midi":        midi_files.get("bass"),
        "drums_midi":       midi_files.get("drums"),
        "instruments_midi": midi_files.get("instruments"),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
