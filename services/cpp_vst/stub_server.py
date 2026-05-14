"""
VST Host stub — Python fallback until the C++ binary is compiled.
Runs on port 8003 and returns the MIDI-derived audio via scipy synthesis.
"""
import os
import json
import struct
import math
import numpy as np
from scipy.io import wavfile
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="VstHost Stub", version="1.0.0-stub")


class RenderRequest(BaseModel):
    midi_path:     str
    vst_path:      str
    output_path:   str
    sample_rate:   int   = 44100
    bpm:           float = 120.0
    duration_secs: int   = 30


@app.get("/health")
def health():
    return {
        "status": "ok",
        "port":   8003,
        "mode":   "python-stub",
        "note":   "C++ VST host not compiled — using sine synthesis fallback",
    }


@app.post("/render")
def render(req: RenderRequest):
    os.makedirs(os.path.dirname(req.output_path) or ".", exist_ok=True)
    try:
        notes = _parse_midi_notes(req.midi_path)
        audio = _synthesise(notes, req.sample_rate, req.duration_secs)
        _write_wav(req.output_path, audio, req.sample_rate)
        return {
            "success":       True,
            "output_path":   req.output_path,
            "duration_secs": req.duration_secs,
            "note_count":    len(notes),
            "mode":          "stub-synthesis",
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/plugins/scan")
def plugins_scan(body: dict = None):
    return {
        "path":    "N/A (stub)",
        "count":   0,
        "plugins": [],
        "note":    "Compile the C++ binary to enable real VST scanning",
    }


# ── Simple MIDI parser ────────────────────────────────────────────────────────

def _parse_midi_notes(midi_path: str) -> list[dict]:
    """Extract note events from a MIDI file (minimal parser)."""
    if not os.path.exists(midi_path):
        return []
    notes = []
    try:
        with open(midi_path, "rb") as f:
            data = f.read()

        i = 0
        ticks_per_beat = 480
        # Read header
        if data[0:4] == b"MThd":
            ticks_per_beat = struct.unpack(">H", data[12:14])[0]
            i = 14

        # Walk tracks
        while i < len(data) - 4:
            if data[i:i+4] == b"MTrk":
                track_len = struct.unpack(">I", data[i+4:i+8])[0]
                track_data = data[i+8: i+8+track_len]
                notes.extend(_parse_track(track_data, ticks_per_beat))
                i += 8 + track_len
            else:
                i += 1
    except Exception:
        pass
    return notes


def _parse_track(data: bytes, ticks_per_beat: int) -> list[dict]:
    tempo = 500000  # default 120 BPM
    notes: dict[int, dict] = {}
    events = []
    i = 0
    tick = 0

    def read_varint():
        nonlocal i
        val = 0
        while i < len(data):
            b = data[i]; i += 1
            val = (val << 7) | (b & 0x7F)
            if not (b & 0x80):
                break
        return val

    last_status = 0
    while i < len(data):
        delta = read_varint()
        tick += delta
        if i >= len(data):
            break
        b = data[i]
        if b & 0x80:
            last_status = b; i += 1
        status = last_status
        stype  = status & 0xF0

        if stype == 0x90 and i + 1 < len(data):  # Note On
            note, vel = data[i], data[i+1]; i += 2
            if vel > 0:
                notes[note] = {"pitch": note, "vel": vel, "start_ticks": tick}
            elif note in notes:
                n = notes.pop(note)
                n["dur_ticks"] = tick - n["start_ticks"]
                events.append(n)
        elif stype == 0x80 and i + 1 < len(data):  # Note Off
            note = data[i]; i += 2
            if note in notes:
                n = notes.pop(note)
                n["dur_ticks"] = tick - n["start_ticks"]
                events.append(n)
        elif stype in (0xA0, 0xB0, 0xE0) and i + 1 < len(data):
            i += 2
        elif stype in (0xC0, 0xD0) and i < len(data):
            i += 1
        elif status == 0xFF and i + 1 < len(data):  # Meta
            mtype = data[i]; i += 1
            mlen  = read_varint()
            if mtype == 0x51 and mlen == 3:
                tempo = (data[i] << 16) | (data[i+1] << 8) | data[i+2]
            i += mlen
        elif status == 0xF0:
            while i < len(data) and data[i] != 0xF7:
                i += 1
            i += 1

    secs_per_tick = (tempo / 1_000_000) / ticks_per_beat
    for e in events:
        e["start_sec"] = e["start_ticks"] * secs_per_tick
        e["dur_sec"]   = max(e.get("dur_ticks", 0) * secs_per_tick, 0.05)
    return events


def _synthesise(notes: list[dict], sr: int, duration: int) -> np.ndarray:
    """Additive sine synthesis per MIDI note."""
    audio = np.zeros((duration * sr, 2), dtype=np.float32)
    for note in notes:
        freq  = 440.0 * (2 ** ((note["pitch"] - 69) / 12))
        amp   = note.get("vel", 80) / 127.0 * 0.3
        start = int(note["start_sec"] * sr)
        dur   = int(note["dur_sec"]   * sr)
        end   = min(start + dur, len(audio))
        if start >= len(audio):
            continue
        t     = np.arange(end - start) / sr
        # Sine + harmonics + simple ADSR envelope
        wave  = (np.sin(2 * math.pi * freq * t) * 0.6 +
                 np.sin(2 * math.pi * freq * 2 * t) * 0.2 +
                 np.sin(2 * math.pi * freq * 3 * t) * 0.1)
        env   = _adsr(len(t), int(sr * 0.01), int(sr * 0.05), 0.7, int(sr * 0.1))
        wave  = (wave * env * amp).astype(np.float32)
        audio[start:end, 0] += wave
        audio[start:end, 1] += wave

    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.85
    return audio


def _adsr(n: int, att: int, dec: int, sus: float, rel: int) -> np.ndarray:
    env = np.ones(n, dtype=np.float32)
    att = min(att, n)
    env[:att] = np.linspace(0, 1, att)
    dec_end = min(att + dec, n)
    env[att:dec_end] = np.linspace(1, sus, dec_end - att)
    rel_start = max(n - rel, att)
    env[rel_start:] = np.linspace(sus, 0, n - rel_start)
    return env


def _write_wav(path: str, audio: np.ndarray, sr: int):
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    wavfile.write(path, sr, pcm)


if __name__ == "__main__":
    uvicorn.run("stub_server:app", host="0.0.0.0", port=8003, reload=False)
