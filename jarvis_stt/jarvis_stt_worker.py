"""
Standalone STT worker — runs as a subprocess, completely isolated from Qt.
Protocol:
  - Reads a JSON line from stdin: {"audio_b64": "<base64 of float32 numpy bytes>"}
  - Writes a JSON line to stdout: {"text": "..."} or {"error": "..."}
"""
import sys, os, json, base64, traceback

MODEL_DIR = sys.argv[1] if len(sys.argv) > 1 else "jarvis_stt"

def main():
    try:
        from faster_whisper import WhisperModel
        # Prefer GPU when available, but fall back cleanly unless strict GPU is requested.
        # Environment overrides:
        #   JARVIS_STT_DEVICE=cpu|cuda|auto
        #   JARVIS_STT_COMPUTE=float16|int8_float16|int8|auto
        #   JARVIS_STT_STRICT_GPU=1  (if set, no fallback; fail if CUDA can't load)
        # Default to CPU for maximum compatibility on Windows.
        device = os.environ.get("JARVIS_STT_DEVICE", "cpu")
        compute_type = os.environ.get("JARVIS_STT_COMPUTE", "int8")
        strict_gpu = os.environ.get("JARVIS_STT_STRICT_GPU", "").strip() in ("1", "true", "True", "YES", "yes")
        try:
            model = WhisperModel(MODEL_DIR, device=device, compute_type=compute_type)
        except Exception:
            if strict_gpu:
                raise
            # Common case on Windows: CUDA not present/configured.
            model = WhisperModel(MODEL_DIR, device="cpu", compute_type="int8")
        # Signal ready
        sys.stdout.write(json.dumps({"status": "ready"}) + "\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(json.dumps({"error": f"load: {e}"}) + "\n")
        sys.stdout.flush()
        sys.exit(1)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            raw = base64.b64decode(req["audio_b64"])
            import numpy as np
            audio_np = np.frombuffer(raw, dtype=np.float32)
            # Fast defaults for interactive assistant usage.
            beam_size = int(os.environ.get("JARVIS_STT_BEAM", "1"))
            language = os.environ.get("JARVIS_STT_LANGUAGE", "en")
            vad_min_silence_ms = int(os.environ.get("JARVIS_STT_VAD_MIN_SILENCE_MS", "350"))
            segments, _ = model.transcribe(
                audio_np,
                beam_size=max(1, beam_size),
                best_of=1,
                language=language,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": max(0, vad_min_silence_ms)},
                condition_on_previous_text=False,
                temperature=0.0,
                word_timestamps=False,
            )
            text = " ".join(s.text.strip() for s in segments).strip()
            sys.stdout.write(json.dumps({"text": text}) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"error": str(e)}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
