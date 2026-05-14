import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from rvc_engine import convert_voice, RVC_OK

try:
    from db import list_models, get_model, add_model, delete_model, set_default
    DB_OK = True
except Exception as e:
    DB_OK = False
    _DB_ERR = str(e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[startup] rvc={RVC_OK}  db={DB_OK}")
    yield


app = FastAPI(title="AudioPipeline RVC Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "port": 8004, "rvc": RVC_OK, "db": DB_OK}


# ── Voice conversion ───────────────────────────────────────────────────────────

class RvcRequest(BaseModel):
    vocal_wav: str
    model_path: str = ""
    index_path: str = ""
    output_path: str
    job_id: str = ""
    f0_up_key: int = 0

@app.post("/rvc")
def rvc(req: RvcRequest):
    if not os.path.exists(req.vocal_wav):
        raise HTTPException(404, f"Vocal file not found: {req.vocal_wav}")

    out_wav = os.path.join(req.output_path, "vocal_rvc.wav")
    try:
        result = convert_voice(
            vocal_wav   = req.vocal_wav,
            model_path  = req.model_path,
            index_path  = req.index_path,
            output_path = out_wav,
            f0_up_key   = req.f0_up_key,
        )
        return {"output_wav": result, "rvc_used": RVC_OK and bool(req.model_path)}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Model management ───────────────────────────────────────────────────────────

@app.get("/models")
def get_models():
    if not DB_OK:
        return {"models": [], "db": False, "error": _DB_ERR}
    return {"models": list_models(), "db": True}


class AddModelRequest(BaseModel):
    name: str
    model_path: str
    index_path: str | None = None
    description: str | None = None

@app.post("/models")
def post_model(req: AddModelRequest):
    if not os.path.exists(req.model_path):
        raise HTTPException(404, f"Model file not found: {req.model_path}")
    if not DB_OK:
        raise HTTPException(503, "Database not available")
    model_id = add_model(req.name, req.model_path, req.index_path, req.description)
    return {"id": model_id, "name": req.name}


@app.delete("/models/{model_id}")
def del_model(model_id: int):
    if not DB_OK:
        raise HTTPException(503, "Database not available")
    delete_model(model_id)
    return {"deleted": model_id}


@app.post("/models/{model_id}/default")
def set_model_default(model_id: int):
    if not DB_OK:
        raise HTTPException(503, "Database not available")
    set_default(model_id)
    return {"default": model_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=False)
