import os

try:
    from basic_pitch.inference import predict
    BASIC_PITCH_OK = True
except Exception:
    BASIC_PITCH_OK = False


def transcribe_stems(stems: dict, output_dir: str) -> dict:
    """Transcribe bass/drums/instruments stems to MIDI. Vocals are skipped."""
    if not BASIC_PITCH_OK:
        return {}

    os.makedirs(output_dir, exist_ok=True)
    midi_files = {}

    for stem_name in ["bass", "drums", "instruments"]:
        stem_path = stems.get(stem_name)
        if stem_path and os.path.exists(stem_path):
            midi_path = os.path.join(output_dir, f"{stem_name}.mid")
            try:
                _, midi_data, _ = predict(stem_path)
                midi_data.write(midi_path)
                midi_files[stem_name] = midi_path
            except Exception as e:
                midi_files[f"{stem_name}_error"] = str(e)

    return midi_files
