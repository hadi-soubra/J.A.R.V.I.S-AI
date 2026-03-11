"""
J.A.R.V.I.S TTS Worker — separate process to avoid onnxruntime/Qt DLL conflicts.

Commands (stdin → worker):
  {"cmd":"prebake", "id":N, "text":"...", "voice":"bm_george", "speed":1.0}
      Synthesize and hold in memory. Returns {"status":"prebaked","id":N,"duration_ms":N}

  {"cmd":"play_prebaked", "id":N}
      Play a prebaked item immediately. Returns {"status":"playing","id":N} then {"status":"done","id":N}

  {"text":"...", "voice":"bm_george", "speed":1.0}
      Synthesize then play (used for responses). Returns {"status":"done"}

  {"cmd":"stop"}   — stop playback, clear queues
  {"cmd":"quit"}   — shut down

Worker responses (stdout):
  {"status":"ready"}
  {"status":"prebaked",   "id":N, "duration_ms":N}
  {"status":"playing",    "id":N}
  {"status":"done",       "id":N}   (id=-1 for speak)
  {"status":"error",      "message":"..."}
"""

import sys, os, json, threading, time
import queue as _queue

def emit(obj):
    print(json.dumps(obj), flush=True)

def main():
    if len(sys.argv) < 3:
        emit({"status":"error","message":"Usage: jarvis_tts_worker.py <model_path> <voices_path>"})
        sys.exit(1)

    model_path  = sys.argv[1]
    voices_path = sys.argv[2]

    try:
        os.environ["ONNX_PROVIDER"] = "CUDAExecutionProvider"
        from kokoro_onnx import Kokoro
        import numpy as np
        kokoro = Kokoro(model_path, voices_path)
        emit({"status":"ready"})
    except Exception as e:
        emit({"status":"error","message":str(e)})
        sys.exit(1)

    SAMPLE_RATE  = 24000
    prebaked     = {}          # id → pcm ndarray
    play_queue   = _queue.Queue()
    stop_evt     = threading.Event()

    def synth(text, voice_id, speed):
        """Synthesize text → (pcm int16 ndarray, duration_ms). Returns (None,0) on error."""
        try:
            samples, _ = kokoro.create(text.strip(), voice=voice_id, speed=speed, lang="en-us")
            pcm = (samples * 32767).clip(-32768, 32767).astype(np.int16)
            duration_ms = int(len(samples) / SAMPLE_RATE * 1000)
            return pcm, duration_ms
        except Exception as e:
            emit({"status":"error","message":f"synth: {e}"})
            return None, 0

    def play_pcm(pcm, item_id):
        """Play pcm array. Blocks until done or stopped."""
        import sounddevice as sd
        stop_evt.clear()
        emit({"status":"playing","id":item_id})
        try:
            sd.play(pcm, samplerate=SAMPLE_RATE, blocking=False)
            duration_s = len(pcm) / SAMPLE_RATE
            elapsed = 0.0
            while elapsed < duration_s:
                if stop_evt.is_set():
                    sd.stop(); break
                time.sleep(0.02)
                elapsed += 0.02
            if not stop_evt.is_set():
                sd.wait()
        except Exception as e:
            emit({"status":"error","message":f"play: {e}"})
        emit({"status":"done","id":item_id})

    # Play thread — serializes all playback
    def play_thread():
        while True:
            item = play_queue.get()
            if item is None: break
            if stop_evt.is_set(): continue
            pcm, item_id = item
            play_pcm(pcm, item_id)

    t_play = threading.Thread(target=play_thread, daemon=True)
    t_play.start()

    # Main stdin loop
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            msg = json.loads(line)
        except Exception:
            continue

        cmd = msg.get("cmd", "")

        if cmd == "quit":
            play_queue.put(None)
            break

        elif cmd == "stop":
            stop_evt.set()
            try:
                import sounddevice as sd; sd.stop()
            except: pass
            while not play_queue.empty():
                try: play_queue.get_nowait()
                except: pass
            prebaked.clear()
            emit({"status":"done","id":-1})

        elif cmd == "prebake":
            # Synthesize and hold — do NOT play yet
            item_id  = msg.get("id", 0)
            text     = msg.get("text","").strip()
            voice_id = msg.get("voice","bm_george")
            speed    = msg.get("speed", 1.0)
            if not text: continue
            pcm, duration_ms = synth(text, voice_id, speed)
            if pcm is not None:
                prebaked[item_id] = pcm
                emit({"status":"prebaked","id":item_id,"duration_ms":duration_ms})

        elif cmd == "play_prebaked":
            item_id = msg.get("id", 0)
            pcm = prebaked.pop(item_id, None)
            if pcm is not None:
                stop_evt.clear()
                play_queue.put((pcm, item_id))

        else:
            # Inline speak: synthesize then queue for playback
            text     = msg.get("text","").strip()
            voice_id = msg.get("voice","bm_george")
            speed    = msg.get("speed", 1.0)
            if not text: continue
            stop_evt.clear()
            pcm, duration_ms = synth(text, voice_id, speed)
            if pcm is not None:
                play_queue.put((pcm, -1))

if __name__ == "__main__":
    main()
