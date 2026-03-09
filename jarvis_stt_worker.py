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
        import numpy as np
        from faster_whisper import WhisperModel
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
            segments, _ = model.transcribe(audio_np, beam_size=5, language="en", vad_filter=True)
            text = " ".join(s.text.strip() for s in segments).strip()
            sys.stdout.write(json.dumps({"text": text}) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"error": str(e)}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
