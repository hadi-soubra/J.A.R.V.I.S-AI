"""
J.A.R.V.I.S Interface — PyQt6
pip install PyQt6 faster-whisper pyaudio kokoro-onnx sounddevice keyboard numpy
"""

import sys, os, json, time, socket, subprocess, threading, base64, datetime, uuid, re
import urllib.request, urllib.error, urllib.parse, io, wave, tempfile, webbrowser

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QComboBox, QSizePolicy,
    QFileDialog, QDialog, QMenu,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QFont, QCursor, QAction, QIcon

# ── Paths ─────────────────────────────────────────────────────────────────────
APP_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(APP_DIR, "jarvis_data")
CONV_DIR  = os.path.join(DATA_DIR, "conversations")
MEM_FILE  = os.path.join(DATA_DIR, "memory.json")
SETT_FILE = os.path.join(DATA_DIR, "settings.json")
VOICE_DIR = os.path.join(APP_DIR, "jarvis_voices")
STT_MODEL_DIR = r"C:\Users\Hadi\Desktop\holder\Jarvis\jarvis_stt"  # local model folder
for _d in [DATA_DIR, CONV_DIR, VOICE_DIR]: os.makedirs(_d, exist_ok=True)

# ── Config ────────────────────────────────────────────────────────────────────
# All tuneable constants in one place. Change these to customise behaviour.
OLLAMA_HOST       = "127.0.0.1"
OLLAMA_PORT       = 11434
OLLAMA_URL        = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
WIN_W, WIN_H      = 400, 780
def _load_api_key():
    key_file = os.path.join(DATA_DIR, "api_key.txt")
    if os.path.exists(key_file):
        return open(key_file, encoding="utf-8").read().strip()
    return "YOUR_API_KEY_HERE"
ANTHROPIC_API_KEY = _load_api_key()
MAX_HISTORY       = 40

VOICES = {
    "MALE":   {"id": "bm_george"},
    "FEMALE": {"id": "af_heart"},
}

PROVIDERS = {
    "LOCAL 4b":  {"type": "ollama",    "model": "qwen3.5:4b"},
    "LOCAL 9b":  {"type": "ollama",    "model": "qwen3.5:9b"},
    "HAIKU":     {"type": "anthropic", "model": "claude-haiku-4-5"},
    "SONNET":    {"type": "anthropic", "model": "claude-sonnet-4-5"},
    "OPUS":      {"type": "anthropic", "model": "claude-opus-4-5"},
}
DEFAULT_PROVIDER = "LOCAL 4b"

IMAGE_EXTS = {".png",".jpg",".jpeg",".webp",".gif"}
TEXT_EXTS  = {".txt",".py",".js",".ts",".html",".css",".md",".json",".csv",
              ".xml",".yaml",".yml",".sh",".bat",".c",".cpp",".h",".java",
              ".rs",".go",".rb",".php"}
PDF_EXT = ".pdf"

JARVIS_SYSTEM = (
    "You are J.A.R.V.I.S (Just A Rather Very Intelligent System), "
    "the personal AI assistant. Be concise, direct, and highly capable. "
    "Address the user as 'sir' occasionally. No unnecessary preamble.\n\n"
    "You can control the PC using special command tags in your response.\n\n"
    "AVAILABLE COMMANDS:\n"
    "[RUN: appname] - launch an app. Apps: zen, spotify, vscode, explorer, outlook, bambu, blender, tlauncher, steam, epicgames, rdr2, sekiro, breadandfred, minecraft, rocketleague\n"
    "[WEB: query or url] - open browser with Google search or URL\n"
    "[INFO: system] - get live CPU, RAM, battery, disk stats\n"
    "[CMD: shutdown] - shutdown the PC (asks confirmation)\n"
    "[CMD: restart] - restart the PC (asks confirmation)\n"
    "[CMD: sleep] - put PC to sleep\n"
    "[CMD: lock] - lock the screen\n"
    "[CMD: high_performance] - High Performance power plan (gaming)\n"
    "[CMD: balanced] - Balanced power plan (normal use)\n"
    "[FILE: open, filename] - find and open a file\n"
    "[FILE: folder, name] - open a folder in Explorer\n"
    "Only use commands when user clearly wants an action. Never use tags in hypothetical responses."
)

# The greeting shown (and spoken) when JARVIS starts or a new chat is opened.
# Edit freely — timing and audio sync recalculate automatically at runtime.
GREETING_TEXT = (
    "Hello, sir.\n\n"
    "JARVIS online and fully operational. "
    "All systems running within normal parameters.\n\n"
    "How may I assist you today?"
)

# ── Colors ────────────────────────────────────────────────────────────────────
# Centralised palette — every UI color comes from here.
BG        = "#030a10"; TITLEBAR = "#040d15"; CTRLBAR  = "#040d15"
USER_BG   = "#051520"; AI_BG   = "#030e18"; THINK_BG = "#020c14"
THINK_FG  = "#1e6e8a"; INPUT_BG= "#040d15"; TEXTAREA = "#051828"
ACCENT    = "#00d4ff"; ACCDIM  = "#005566"; TEXT     = "#a8f0ff"
TEXTMUT   = "#1a5060"; TEXTDIM = "#0e3040"; ERR      = "#ff4444"
OK_COL    = "#00ffaa"; WARN    = "#ffaa00"; STATFG   = "#00aacc"
BORDER    = "#0a3a4a"; CLAUDE_COL = "#a855f7"

COMBO_SS = lambda color: f"""
    QComboBox{{background:#000d14;color:{color};border:1px solid {ACCDIM};
               padding:2px 8px;min-width:90px;}}
    QComboBox:hover{{border-color:{ACCENT};}}
    QComboBox QAbstractItemView{{background:#000d14;color:{color};
        selection-background-color:{ACCDIM};border:1px solid {ACCDIM};}}
    QComboBox::drop-down{{border:none;}}
    QComboBox::down-arrow{{image:none;width:0;height:0;
        border-left:4px solid transparent;border-right:4px solid transparent;
        border-top:5px solid {color};margin-right:6px;}}
"""

MENU_SS = f"""
    QMenu{{background:#000d14;color:{TEXT};border:1px solid {ACCDIM};padding:4px 0;}}
    QMenu::item{{padding:6px 20px 6px 12px;font-family:'Courier New';font-size:9pt;}}
    QMenu::item:selected{{background:{ACCDIM};color:{ACCENT};}}
    QMenu::separator{{height:1px;background:{ACCDIM};margin:4px 0;}}
"""

# ── Settings ─────────────────────────────────────────────────────────────────
# Persists user preferences (provider, voice, TTS on/off, etc.) to a JSON file.─
def load_settings():
    try:
        with open(SETT_FILE) as f: return json.load(f)
    except Exception: return {}

def save_settings(d):
    with open(SETT_FILE,"w") as f: json.dump(d,f,indent=2)

# ── Memory ────────────────────────────────────────────────────────────────────
# Persistent facts JARVIS remembers across conversations (manually managed by user).
def load_memory():
    try:
        with open(MEM_FILE) as f: return json.load(f)
    except Exception: return {"facts":[]}

def save_memory(mem):
    with open(MEM_FILE,"w") as f: json.dump(mem,f,indent=2)

def memory_prompt(mem):
    facts=mem.get("facts",[])
    if not facts: return ""
    return "\n\nWhat I know about the user:\n"+"\n".join(f"- {f}" for f in facts)

# ── Conversations ─────────────────────────────────────────────────────────────
# Each conversation is saved as a JSON file keyed by UUID in jarvis_data/convs/.
def conv_path(cid): return os.path.join(CONV_DIR,f"{cid}.json")

def save_conv(cid,title,history):
    with open(conv_path(cid),"w") as f:
        json.dump({"id":cid,"title":title,
                   "updated":datetime.datetime.now().isoformat(),
                   "history":history},f,indent=2)

def load_conv(cid):
    with open(conv_path(cid)) as f: return json.load(f)

def delete_conv(cid):
    try: os.remove(conv_path(cid))
    except Exception: pass

def list_convs():
    convs=[]
    for fn in os.listdir(CONV_DIR):
        if fn.endswith(".json"):
            try:
                with open(os.path.join(CONV_DIR,fn)) as f: d=json.load(f)
                convs.append(d)
            except Exception: pass
    convs.sort(key=lambda x:x.get("updated",""),reverse=True)
    return convs

def conv_title(history):
    for m in history:
        if m.get("role")=="user":
            c=m.get("content","")
            if isinstance(c,list):
                c=next((x["text"] for x in c if x.get("type")=="text"),"[media]")
            t=str(c)[:40].replace("\n"," ")
            return t or "Untitled"
    return "Untitled"

# ── File helpers ─────────────────────────────────────────────────────────────
# Reads attachments (images, PDFs, text) and builds provider-specific message dicts.─
def read_file(path):
    ext=os.path.splitext(path)[1].lower(); name=os.path.basename(path)
    with open(path,"rb") as f: raw=f.read()
    b64=base64.standard_b64encode(raw).decode()
    if ext in IMAGE_EXTS:
        mime={".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",
              ".webp":"image/webp",".gif":"image/gif"}.get(ext,"image/png")
        return {"kind":"image","name":name,"b64":b64,"mime":mime}
    elif ext==PDF_EXT:
        return {"kind":"pdf","name":name,"b64":b64,"mime":"application/pdf"}
    elif ext in TEXT_EXTS:
        try: text=raw.decode("utf-8")
        except: text=raw.decode("latin-1")
        return {"kind":"text","name":name,"text":text}
    else:
        try: return {"kind":"text","name":name,"text":raw.decode("utf-8")}
        except: return None

def build_ollama_msg(text,attachments):
    images=[a["b64"] for a in attachments if a["kind"]=="image"]
    parts=[]
    for a in attachments:
        if a["kind"]=="text": parts.append(f"[FILE: {a['name']}]\n```\n{a['text']}\n```")
        elif a["kind"]=="pdf": parts.append(f"[PDF: {a['name']}]")
    if text: parts.append(text)
    msg={"role":"user","content":"\n\n".join(parts)}
    if images: msg["images"]=images
    return msg

def build_anthropic_msg(text,attachments):
    content=[]
    for a in attachments:
        if a["kind"]=="image":
            content.append({"type":"image","source":{"type":"base64","media_type":a["mime"],"data":a["b64"]}})
        elif a["kind"]=="pdf":
            content.append({"type":"document","source":{"type":"base64","media_type":"application/pdf","data":a["b64"]}})
        elif a["kind"]=="text":
            content.append({"type":"text","text":f"[FILE: {a['name']}]\n```\n{a['text']}\n```"})
    if text: content.append({"type":"text","text":text})
    return {"role":"user","content":content}

# ── Network ──────────────────────────────────────────────────────────────────
# Ollama connectivity helpers + streaming functions for both Ollama and Anthropic.─
def tcp_up(timeout=2):
    try:
        s=socket.create_connection((OLLAMA_HOST,OLLAMA_PORT),timeout=timeout)
        s.close(); return True
    except OSError: return False

def start_ollama():
    try:
        kw={"stdout":subprocess.DEVNULL,"stderr":subprocess.DEVNULL}
        if sys.platform=="win32":
            kw["creationflags"]=subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS
        subprocess.Popen(["ollama","serve"],**kw); return True
    except FileNotFoundError: return False

def wait_ollama(max_wait=20):
    if tcp_up(1): return True,"ready"
    if not start_ollama(): return False,"Ollama not found"
    for _ in range(max_wait):
        time.sleep(1)
        if tcp_up(1): return True,"started"
    return False,f"No response after {max_wait}s"

def stream_ollama(model,messages,think):
    payload=json.dumps({"model":model,"messages":messages,"stream":True,
                        "think":think,"options":{"temperature":0.7}}).encode()
    req=urllib.request.Request(f"{OLLAMA_URL}/api/chat",data=payload,
                               headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=None) as r:
        for line in r:
            s=line.decode().strip()
            if s: yield s

def stream_anthropic(model,messages,system_text,api_key):
    api_msgs=[{"role":m["role"],"content":m["content"]}
              for m in messages if m["role"] in ("user","assistant")]
    payload=json.dumps({"model":model,"max_tokens":8096,"stream":True,
                        "system":system_text,"messages":api_msgs}).encode()
    req=urllib.request.Request("https://api.anthropic.com/v1/messages",data=payload,
        headers={"Content-Type":"application/json","x-api-key":api_key,
                 "anthropic-version":"2023-06-01"},method="POST")
    with urllib.request.urlopen(req,timeout=None) as r:
        for line in r:
            s=line.decode().strip()
            if s.startswith("data:"):
                d=s[5:].strip()
                if d and d!="[DONE]":
                    try: yield json.loads(d)
                    except Exception: pass

# ── TTS Worker script path ────────────────────────────────────────────────────
TTS_WORKER_SCRIPT = os.path.join(APP_DIR, "jarvis_tts_worker.py")

# ── TTS Engine (kokoro-onnx via subprocess) ───────────────────────────────────
class TTSEngine:
    """
    Kokoro-onnx TTS engine running in a separate subprocess.

    Modes:
      prebake(id, text, voice) — synthesize + hold, fires prebake_cb(id, duration_ms)
      play_prebaked(id)        — play a prebaked item
      speak(text, voice)       — synthesize then play (responses)
      stop()                   — stop everything immediately
    """
    MODEL_FILE  = "kokoro-v1.0.fp16-gpu.onnx"
    VOICES_FILE = "voices-v1.0.bin"

    def __init__(self, status_cb=None, prebake_cb=None, done_cb=None):
        self._proc        = None
        self._ready       = threading.Event()
        self._status_cb   = status_cb
        self._prebake_cb  = prebake_cb   # (id, duration_ms) when prebake finishes
        self._done_cb     = done_cb      # (id) when playback finishes
        self._voice       = "MALE"
        self._write_lock  = threading.Lock()
        threading.Thread(target=self._start, daemon=True).start()

    def _set_status(self, msg, level="warn"):
        if self._status_cb: self._status_cb(msg, level)

    def _start(self):
        try:
            model_path  = os.path.join(VOICE_DIR, self.MODEL_FILE)
            voices_path = os.path.join(VOICE_DIR, self.VOICES_FILE)
            kw = dict(stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                      stderr=subprocess.DEVNULL, text=True, bufsize=1)
            if sys.platform == "win32":
                kw["creationflags"] = subprocess.CREATE_NO_WINDOW
            self._set_status("◈  LOADING KOKORO…", "warn")
            self._proc = subprocess.Popen(
                [sys.executable, TTS_WORKER_SCRIPT, model_path, voices_path], **kw)
            line = self._proc.stdout.readline()
            msg  = json.loads(line)
            if msg.get("status") == "ready":
                self._set_status("◈  TTS READY", "ok")
                print("[TTS] Kokoro worker ready")
                self._ready.set()
                threading.Thread(target=self._reader, daemon=True).start()
            else:
                print(f"[TTS] Worker failed: {msg.get('message','')}")
                self._set_status("⚠  TTS FAILED", "err")
                self._ready.set()
        except Exception as e:
            print(f"[TTS] Failed to start worker: {e}")
            self._set_status("⚠  TTS FAILED", "err")
            self._ready.set()

    def _reader(self):
        while self._proc and self._proc.poll() is None:
            try:
                line = self._proc.stdout.readline()
                if not line: break
                msg = json.loads(line.strip())
                status = msg.get("status","")
                if status == "prebaked" and self._prebake_cb:
                    self._prebake_cb(msg.get("id",0), msg.get("duration_ms",0))
                elif status == "done" and self._done_cb:
                    self._done_cb(msg.get("id",-1))
            except Exception:
                pass

    def _send(self, payload):
        with self._write_lock:
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.stdin.write(json.dumps(payload) + "\n")
                    self._proc.stdin.flush()
                    return True
                except Exception as e:
                    print(f"[TTS] Send error: {e}")
        return False

    def prebake(self, item_id, text, voice_name=None):
        """Synthesize and hold. prebake_cb fires when ready."""
        if not text.strip(): return
        if voice_name is None: voice_name = self._voice
        voice_id = VOICES[voice_name]["id"]
        self._ready.wait(timeout=30)
        self._send({"cmd":"prebake","id":item_id,"text":text,"voice":voice_id,"speed":1.0})

    def play_prebaked(self, item_id):
        """Play a previously prebaked item."""
        self._send({"cmd":"play_prebaked","id":item_id})

    def speak(self, text, voice_name=None):
        """Synthesize then play immediately (for responses)."""
        if not text.strip(): return
        if voice_name is None: voice_name = self._voice
        voice_id = VOICES[voice_name]["id"]
        self._ready.wait(timeout=30)
        self._send({"text":text,"voice":voice_id,"speed":1.0})

    def set_voice(self, name):
        self._voice = name

    def stop(self):
        self._send({"cmd":"stop"})

    def is_ready(self):
        return self._ready.is_set() and self._proc is not None and self._proc.poll() is None
_tts = None

# ── STT Subprocess manager ────────────────────────────────────────────────────
# faster-whisper (ctranslate2) crashes when loaded in the same process as Qt on
# Windows. We run it in a completely separate Python process and talk via JSON
# over stdin/stdout — zero shared memory, zero DLL conflicts.

STT_WORKER_SCRIPT = os.path.join(APP_DIR, "jarvis_stt_worker.py")

class STTProcess:
    """
    Manages a persistent background Python process for speech-to-text.
    faster-whisper (ctranslate2) crashes when loaded in the same process as Qt on
    Windows due to DLL conflicts. This class runs jarvis_stt_worker.py as a
    completely separate Python process and communicates via JSON over stdin/stdout.
    The worker process loads the Whisper model once at startup and reuses it.
    """
    def __init__(self, status_cb=None):
        self._proc       = None
        self._lock       = threading.Lock()
        self._ready      = threading.Event()
        self._status_cb  = status_cb
        threading.Thread(target=self._start, daemon=True).start()

    def _start(self):
        try:
            kw = dict(stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                      stderr=subprocess.DEVNULL, text=True, bufsize=1)
            if sys.platform == "win32":
                kw["creationflags"] = subprocess.CREATE_NO_WINDOW
            self._proc = subprocess.Popen(
                [sys.executable, STT_WORKER_SCRIPT, STT_MODEL_DIR], **kw)
            # Wait for "ready" line
            line = self._proc.stdout.readline()
            msg  = json.loads(line)
            if "error" in msg:
                print(f"[STT] Worker failed to load: {msg['error']}")
                if self._status_cb: self._status_cb("⚠  STT LOAD FAILED", "err")
            else:
                print("[STT] Subprocess worker ready")
                if self._status_cb: self._status_cb("◈  STT READY", "ok")
            self._ready.set()
        except Exception as e:
            print(f"[STT] Failed to start worker process: {e}")
            self._ready.set()

    def transcribe(self, audio_np):
        """Send audio to subprocess, return transcribed text (blocking)."""
        import numpy as np, base64
        self._ready.wait(timeout=30)
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                raise RuntimeError("STT worker process is not running")
            b64 = base64.b64encode(audio_np.astype(np.float32).tobytes()).decode()
            self._proc.stdin.write(json.dumps({"audio_b64": b64}) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError("STT worker process died")
            result = json.loads(line)
            if "error" in result:
                raise RuntimeError(result["error"])
            return result.get("text", "")

    def is_ready(self):
        return self._ready.is_set() and self._proc is not None and self._proc.poll() is None

_stt_proc = None   # initialised in MainWindow.__init__

# ── Stream Worker ─────────────────────────────────────────────────────────────
# Runs the AI streaming request on a background thread.
# Emits signals back to the main thread: chunk (text), think_chunk (reasoning),
# sentence (complete sentence for TTS), stats (tokens/sec), finished (done/aborted).
class StreamWorker(QThread):
    chunk       = pyqtSignal(str)
    think_chunk = pyqtSignal(str)
    sentence    = pyqtSignal(str)
    stats       = pyqtSignal(float,int,float)
    finished    = pyqtSignal(str,bool)

    def __init__(self,prov,messages,system_text,think_on,stop_evt):
        super().__init__()
        self.prov=prov; self.messages=messages; self.system_text=system_text
        self.think_on=think_on; self.stop_evt=stop_evt

    def run(self):
        model=self.prov["model"]; ptype=self.prov["type"]
        full=""; t0=time.time(); tok=0; sentence_buf=""
        try:
            if ptype=="ollama":
                if not tcp_up(3): raise ConnectionError(f"Cannot reach Ollama on port {OLLAMA_PORT}.")
                for raw in stream_ollama(model,self.messages,self.think_on):
                    if self.stop_evt.is_set(): break
                    try: data=json.loads(raw)
                    except Exception: continue
                    msg=data.get("message",{})
                    tc=msg.get("thinking","")
                    if tc and self.think_on: self.think_chunk.emit(tc)
                    rc=msg.get("content","")
                    if rc:
                        full+=rc; tok+=1; el=time.time()-t0
                        sentence_buf+=rc
                        self.chunk.emit(full)
                        self.stats.emit(tok/el if el else 0,tok,el)
                        sentence_buf=self._flush_sentences(sentence_buf)
                    if data.get("done"):
                        ec=data.get("eval_count",tok); ed=data.get("eval_duration",0)
                        tps=ec/(ed/1e9) if ed>0 else tok/max(time.time()-t0,.001)
                        self.stats.emit(tps,ec,time.time()-t0)
            else:
                if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY.strip() in ("","YOUR_API_KEY_HERE"):
                    raise ValueError("Anthropic API key not set.")
                for event in stream_anthropic(model,self.messages,self.system_text,ANTHROPIC_API_KEY):
                    if self.stop_evt.is_set(): break
                    etype=event.get("type","")
                    if etype=="content_block_delta":
                        delta=event.get("delta",{})
                        if delta.get("type")=="text_delta":
                            chunk=delta.get("text","")
                            full+=chunk; tok+=1; el=time.time()-t0
                            sentence_buf+=chunk
                            self.chunk.emit(full)
                            self.stats.emit(tok/el if el else 0,tok,el)
                            sentence_buf=self._flush_sentences(sentence_buf)
                    elif etype=="message_delta":
                        ot=event.get("usage",{}).get("output_tokens",tok); el=time.time()-t0
                        self.stats.emit(ot/el if el else 0,ot,el)
            if sentence_buf.strip() and not self.stop_evt.is_set():
                self.sentence.emit(sentence_buf.strip())
        except Exception as e:
            self.finished.emit("⚠  "+str(e),False); return
        self.finished.emit(full,self.stop_evt.is_set())

    def _flush_sentences(self, buf):
        # Split on sentence-ending punctuation, keeping delimiter attached to the left part.
        # e.g. "Hello sir. How are you" → ["Hello sir.", "How are you"]
        parts = re.split(r'(?<=[.!?]) +', buf)  # space only, not \n
        # Only emit sentences we're sure are complete — i.e. NOT the last fragment,
        # which may still be mid-sentence. Requires at least 2 parts.
        if len(parts) < 2:
            return buf  # nothing confirmed complete yet, keep buffering
        for sentence in parts[:-1]:
            s = sentence.strip()
            if s:
                self.sentence.emit(s)
        return parts[-1]  # trailing incomplete fragment, keep for next chunk

# ── Ollama Init Worker ────────────────────────────────────────────────────────
# Runs wait_ollama() on a background thread at startup so the UI never blocks.
# Emits done(ok, message) when Ollama is confirmed up or timed out.
class OllamaInitWorker(QThread):
    done=pyqtSignal(bool,str)
    def run(self): self.done.emit(*wait_ollama())

# ── PC Control — app launcher & tools ─────────────────────────────────────────
# Edit this dictionary to add/remove apps. Key = name to say, value = path or URI.
APPS = {
    # Browsers & productivity
    "zen":              r"C:\Program Files\Zen Browser\zen.exe",
    "browser":          r"C:\Program Files\Zen Browser\zen.exe",
    "spotify":          r"C:\Users\Hadi\AppData\Roaming\Spotify\Spotify.exe",
    "music":          r"C:\Users\Hadi\AppData\Roaming\Spotify\Spotify.exe",
    "vscode":           r"C:\Users\Hadi\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "code":             r"C:\Users\Hadi\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "explorer":         "explorer.exe",
    "files":            "explorer.exe",
    "outlook":          r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
    "email":          r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
    # Creative
    "bambu":            r"C:\Program Files\Bambu Studio\bambu-studio.exe",
    "bamboo":           r"C:\Program Files\Bambu Studio\bambu-studio.exe",
    "slicer":           r"C:\Program Files\Bambu Studio\bambu-studio.exe",
    "blender":          r"C:\Program Files\Blender Foundation\Blender 5.0\blender-launcher.exe",
    # Launchers
    "steam":            r"C:\Program Files (x86)\Steam\steam.exe",
    "epicgames":        r"C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
    "epic":             r"C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
    # Games
    "rdr2":             "steam://rungameid/1174180",
    "red dead":         "steam://rungameid/1174180",
    "rdr":              "steam://rungameid/1174180",
    "sekiro":           "steam://rungameid/814380",
    "rocketleague":     "com.epicgames.launcher://apps/9773aa1aa54f4f7b80e44bef04986cea%3A530145df28a24424923f5828cc9031a1%3ASugar?action=launch&silent=true",
    "rocket league":    "com.epicgames.launcher://apps/9773aa1aa54f4f7b80e44bef04986cea%3A530145df28a24424923f5828cc9031a1%3ASugar?action=launch&silent=true",
    "breadandfred":     r"C:\Bread.and.Fred.v2025.03.07(1)\Bread.and.Fred.v2025.03.07\Bread.and.Fred.v2025.03.07\Bread&Fred.exe",
    "bread and fred":   r"C:\Bread.and.Fred.v2025.03.07(1)\Bread.and.Fred.v2025.03.07\Bread.and.Fred.v2025.03.07\Bread&Fred.exe",
    "tlauncher":        r"C:\Users\Hadi\AppData\Roaming\.minecraft\TLauncher.exe",
    "minecraft":        r"C:\Users\Hadi\AppData\Roaming\.minecraft\TLauncher.exe",
}

# Folders JARVIS is allowed to search for files in
ALLOWED_DIRS = [
    os.path.expanduser("~\\Desktop"),
    os.path.expanduser("~\\Documents"),
    os.path.expanduser("~\\Downloads"),
]

def _get_system_info():
    """Return formatted live system stats via psutil."""
    try:
        import psutil
        cpu  = psutil.cpu_percent(interval=0.5)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        bat  = psutil.sensors_battery()
        lines = [
            f"CPU:     {cpu:.1f}%",
            f"RAM:     {ram.percent:.1f}%  ({ram.used//1024**3:.1f} GB / {ram.total//1024**3:.1f} GB)",
            f"Disk C:  {disk.percent:.1f}%  ({disk.free//1024**3:.1f} GB free)",
        ]
        if bat:
            status = "Charging" if bat.power_plugged else "Discharging"
            lines.append(f"Battery: {bat.percent:.0f}%  ({status})")
        return "\n".join(lines)
    except ImportError:
        return "psutil not installed. Run: pip install psutil"
    except Exception as e:
        return f"Could not get system info: {e}"

def _find_file(name):
    """Search ALLOWED_DIRS for a file matching name (case-insensitive)."""
    name_lower = name.lower()
    for root_dir in ALLOWED_DIRS:
        for dirpath, _, files in os.walk(root_dir):
            for f in files:
                if name_lower in f.lower():
                    return os.path.join(dirpath, f)
    return None

def execute_pc_command(tag, arg, confirm_cb=None):
    """Route a parsed [TAG: arg] to the correct PC action. Returns result string."""
    tag = tag.upper().strip()
    arg = arg.strip()

    if tag == "RUN":
        key = arg.lower().strip()
        path = APPS.get(key)
        if not path:
            for k, v in APPS.items():
                if k in key or key in k:
                    path = v; break
        if path:
            try:
                if any(path.startswith(p) for p in ("steam://", "com.epicgames.", "http")):
                    webbrowser.open(path)
                else:
                    kw = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform=="win32" else {}
                    subprocess.Popen([path], **kw)
                return f"Launched {arg}."
            except Exception as e:
                return f"Failed to launch {arg}: {e}"
        return f"App '{arg}' not found. Add it to the APPS dictionary in jarvis.pyw."

    elif tag == "WEB":
        try:
            url = arg if arg.startswith("http") else f"https://www.google.com/search?q={urllib.parse.quote(arg)}"
            webbrowser.open(url)
            return f"Opened browser: {arg}"
        except Exception as e:
            return f"Browser failed: {e}"

    elif tag == "INFO":
        return _get_system_info()

    elif tag == "CMD":
        cmd = arg.lower().strip()
        if cmd in ("shutdown", "restart"):
            if confirm_cb and not confirm_cb(f"Are you sure you want to {cmd}?"):
                return f"{cmd.capitalize()} cancelled."
        try:
            if   cmd == "shutdown":
                subprocess.run(["shutdown", "/s", "/t", "10"]); return "Shutting down in 10 seconds."
            elif cmd == "restart":
                subprocess.run(["shutdown", "/r", "/t", "10"]); return "Restarting in 10 seconds."
            elif cmd == "sleep":
                subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"]); return "Going to sleep."
            elif cmd == "lock":
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"]); return "Screen locked."
            elif cmd == "high_performance":
                subprocess.run(["powercfg", "/s", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"], shell=True)
                return "Switched to High Performance power plan."
            elif cmd == "balanced":
                subprocess.run(["powercfg", "/s", "381b4222-f694-41f0-9685-ff5bb260df2e"], shell=True)
                return "Switched to Balanced power plan."
            else:
                return f"Unknown command: {cmd}"
        except Exception as e:
            return f"Command failed: {e}"

    elif tag == "FILE":
        parts = arg.split(",", 1)
        op    = parts[0].strip().lower()
        param = parts[1].strip() if len(parts) > 1 else ""
        if op == "open":
            path = _find_file(param)
            if path:
                try: os.startfile(path); return f"Opened: {path}"
                except Exception as e: return f"Could not open: {e}"
            return f"File '{param}' not found in Desktop, Documents, or Downloads."
        elif op == "folder":
            folders = {
                "desktop":   os.path.expanduser("~\\Desktop"),
                "documents": os.path.expanduser("~\\Documents"),
                "downloads": os.path.expanduser("~\\Downloads"),
                "music":     os.path.expanduser("~\\Music"),
                "pictures":  os.path.expanduser("~\\Pictures"),
                "videos":    os.path.expanduser("~\\Videos"),
            }
            path = folders.get(param.lower(), param)
            try: subprocess.Popen(["explorer.exe", path]); return f"Opened folder: {path}"
            except Exception as e: return f"Could not open folder: {e}"
    return None

def parse_commands(text):
    """Extract all [TAG: arg] command tags from model response text."""
    return re.findall(r'\[([A-Z]+):\s*([^\]]+)\]', text, re.IGNORECASE)

# ── UI helpers ───────────────────────────────────────────────────────────────
# Small factory functions used throughout the UI to keep widget creation concise.─
def make_font(family="Courier New",size=10,bold=False,italic=False):
    f=QFont(family,size)
    if bold: f.setBold(True)
    if italic: f.setItalic(True)
    return f

def lbl(text,color=TEXT,font=None):
    l=QLabel(text); l.setStyleSheet(f"color:{color};background:transparent;")
    if font: l.setFont(font)
    return l

def hline(color=ACCENT):
    f=QFrame(); f.setFrameShape(QFrame.Shape.HLine); f.setFixedHeight(1)
    f.setStyleSheet(f"background:{color};border:none;"); return f

# ── Attachment chip ───────────────────────────────────────────────────────────
class AttachChip(QWidget):
    removed=pyqtSignal(object)
    def __init__(self,attachment,parent=None):
        super().__init__(parent)
        self.attachment=attachment
        self.setStyleSheet(f"background:{ACCDIM};border-radius:3px;")
        row=QHBoxLayout(self); row.setContentsMargins(6,2,4,2); row.setSpacing(4)
        icon={"image":"🖼","pdf":"📄","text":"📝"}.get(attachment["kind"],"📎")
        name=attachment["name"]
        if len(name)>18: name=name[:15]+"…"
        l=QLabel(f"{icon} {name}"); l.setFont(make_font(size=8))
        l.setStyleSheet(f"color:{TEXT};background:transparent;"); row.addWidget(l)
        x=QPushButton("×"); x.setFixedSize(14,14); x.setFont(make_font(size=8,bold=True))
        x.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXTMUT};border:none;padding:0;}}"
                        f"QPushButton:hover{{color:{ERR};}}")
        x.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        x.clicked.connect(lambda: self.removed.emit(self)); row.addWidget(x)

# ── Prompt box ────────────────────────────────────────────────────────────────
PROMPT_MIN_H=42; PROMPT_MAX_H=200

class PromptBox(QTextEdit):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setFont(make_font())
        self._normal_ss = (f"QTextEdit{{background:{TEXTAREA};color:{OK_COL};border:none;"
                           f"padding:8px 10px;selection-background-color:{ACCDIM};}}")
        self.setStyleSheet(self._normal_ss)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.document().setDocumentMargin(0)
        self.setFixedHeight(PROMPT_MIN_H)
        self.document().contentsChanged.connect(self._update_height)
        self._stt_active = False   # True while recording or transcribing
        self._saved_text = ""      # text saved before STT takes over

    def set_stt_state(self, state):
        """state: 'recording' | 'transcribing' | 'idle'"""
        if state == "recording":
            self._stt_active = True
            self._saved_text = self.toPlainText()
            self.setReadOnly(True)
            self.setStyleSheet(
                f"QTextEdit{{background:#1a0505;color:{ERR};border:1px solid {ERR};"
                f"padding:8px 10px;selection-background-color:{ACCDIM};}}")
            self.setPlainText("  ●  RECORDING…")
            self.setFixedHeight(PROMPT_MIN_H)
        elif state == "transcribing":
            self.setStyleSheet(
                f"QTextEdit{{background:#0d0d05;color:{WARN};border:1px solid {WARN};"
                f"padding:8px 10px;selection-background-color:{ACCDIM};}}")
            self.setPlainText("  ◈  TRANSCRIBING…")
            self.setFixedHeight(PROMPT_MIN_H)
        else:  # idle — restore
            self._stt_active = False
            self.setReadOnly(False)
            self.setStyleSheet(self._normal_ss)
            self.setPlainText(self._saved_text)
            cursor = self.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.setTextCursor(cursor)
            self._update_height()

    def _update_height(self):
        if self._stt_active: return   # don't resize during STT states
        self.document().setTextWidth(self.viewport().width() or WIN_W-40)
        h=int(self.document().size().height())+20
        self.setFixedHeight(max(PROMPT_MIN_H,min(PROMPT_MAX_H,h)))

    def resizeEvent(self,e):
        super().resizeEvent(e); self._update_height()

# ── Message bubble ────────────────────────────────────────────────────────────
class MessageBubble(QTextEdit):
    def __init__(self,text="",bg=AI_BG,fg=TEXT,italic=False,parent=None):
        super().__init__(parent)
        self.setReadOnly(True); self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFont(make_font(italic=italic))
        self.setStyleSheet(f"QTextEdit{{background:{bg};color:{fg};border:none;padding:10px;"
                           f"selection-background-color:{ACCDIM};selection-color:{TEXT};}}")
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        self.document().setDocumentMargin(0)
        if text: super().setText(text)
        QTimer.singleShot(0,self._update_height)

    def setText(self,text):
        super().setText(text); QTimer.singleShot(0,self._update_height)

    def _update_height(self):
        w=self.viewport().width()
        if w<10: w=WIN_W-60
        self.document().setTextWidth(w)
        h=int(self.document().size().height())+24
        self.setFixedHeight(max(40,h))

    def resizeEvent(self,e):
        super().resizeEvent(e); self._update_height()

# ── Think block ───────────────────────────────────────────────────────────────
class ThinkBlock(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{THINK_BG};")
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        self._btn=QPushButton("// PROCESSING //"); self._btn.setFont(make_font(size=8))
        self._btn.setStyleSheet(f"QPushButton{{background:{THINK_BG};color:{THINK_FG};"
                                f"border:none;text-align:left;padding:4px 10px;}}"
                                f"QPushButton:hover{{color:{ACCENT};}}")
        self._btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn.clicked.connect(self._toggle); layout.addWidget(self._btn)
        self._body=MessageBubble(bg=THINK_BG,fg=THINK_FG,italic=True)
        layout.addWidget(self._body); self._collapsed=False

    def append_think(self,text): self._body.setText(self._body.toPlainText()+text)
    def set_done(self): self._btn.setText("// PROCESSING COMPLETE  [ click to collapse ]")
    def set_aborted(self): self._btn.setText("// ABORTED")
    def _toggle(self):
        self._collapsed=not self._collapsed
        self._body.setVisible(not self._collapsed)
        state="[ COLLAPSED ]" if self._collapsed else "[ EXPANDED ]"
        base=self._btn.text().split("[")[0].strip()
        self._btn.setText(f"{base}  {state}")

# ── AI message ────────────────────────────────────────────────────────────────
class AIMessage(QWidget):
    _THROAT_FRAMES = [
        "  CLEARING THROAT  ●○○",
        "  CLEARING THROAT  ○●○",
        "  CLEARING THROAT  ○○●",
        "  CLEARING THROAT  ○●○",
    ]

    def __init__(self,show_think=True,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG};")
        layout=QVBoxLayout(self); layout.setContentsMargins(10,8,10,4); layout.setSpacing(2)
        layout.addWidget(lbl("[ J.A.R.V.I.S ]",ACCENT,make_font(bold=True,size=9)))
        self.think_block=None
        if show_think:
            self.think_block=ThinkBlock(); layout.addWidget(self.think_block)
        self.resp=MessageBubble(text="▌"); layout.addWidget(self.resp)
        copy_row=QWidget(); copy_row.setStyleSheet(f"background:{BG};")
        cr=QHBoxLayout(copy_row); cr.setContentsMargins(0,0,0,4)
        self.copy_btn=QPushButton("[ COPY ]"); self.copy_btn.setFont(make_font(size=8))
        self.copy_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXTMUT};"
                                    f"border:none;padding:2px 6px;}}"
                                    f"QPushButton:hover{{color:{ACCENT};}}")
        self.copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.copy_btn.clicked.connect(self._copy)
        cr.addStretch(); cr.addWidget(self.copy_btn); layout.addWidget(copy_row)
        self._throat_timer = QTimer(self)
        self._throat_timer.timeout.connect(self._throat_step)
        self._throat_frame = 0

    def start_throat_clearing(self):
        """Show pulsing CLEARING THROAT animation while waiting for first TTS prebake."""
        self._throat_frame = 0
        self.resp.setStyleSheet(f"color:{WARN};background:transparent;padding:4px 0;")
        self.resp.setText(self._THROAT_FRAMES[0])
        self._throat_timer.start(220)
        # Play cough sound in background thread — no DLL conflict, sounddevice only
        def _play_cough():
            try:
                import sounddevice as sd
                import numpy as np
                import wave as _wave
                cough_path = os.path.join(VOICE_DIR, "cough.wav")
                if not os.path.exists(cough_path): return
                with _wave.open(cough_path, 'rb') as wf:
                    sr  = wf.getframerate()
                    ch  = wf.getnchannels()
                    raw = wf.readframes(wf.getnframes())
                pcm = np.frombuffer(raw, dtype=np.int16).reshape(-1, ch)
                sd.play(pcm, samplerate=sr, blocking=True)
            except Exception as e:
                print(f"[COUGH] {e}")
        threading.Thread(target=_play_cough, daemon=True).start()

    def _throat_step(self):
        self._throat_frame = (self._throat_frame + 1) % len(self._THROAT_FRAMES)
        self.resp.setText(self._THROAT_FRAMES[self._throat_frame])

    def stop_throat_clearing(self):
        self._throat_timer.stop()
        self.resp.setStyleSheet(f"color:{TEXT};background:transparent;padding:4px 0;")

    def update_resp(self,text): self.resp.setText(text)
    def update_think(self,text):
        if self.think_block: self.think_block.append_think(text)
    def finalize(self,text,aborted):
        self._throat_timer.stop()
        self.resp.setStyleSheet(f"color:{TEXT};background:transparent;padding:4px 0;")
        self.resp.setText(text+("\n\n[ ABORTED ]" if aborted else ""))
        if self.think_block:
            if aborted: self.think_block.set_aborted()
            else: self.think_block.set_done()
    def _copy(self):
        QApplication.clipboard().setText(self.resp.toPlainText())
        self.copy_btn.setText("[ COPIED ✓ ]")
        self.copy_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{OK_COL};border:none;padding:2px 6px;}}")
        QTimer.singleShot(1800,self._reset_copy)
    def _reset_copy(self):
        self.copy_btn.setText("[ COPY ]")
        self.copy_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXTMUT};"
                                    f"border:none;padding:2px 6px;}}"
                                    f"QPushButton:hover{{color:{ACCENT};}}")

# ── User message ──────────────────────────────────────────────────────────────
class UserMessage(QWidget):
    def __init__(self,text,attachments=None,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG};")
        layout=QVBoxLayout(self); layout.setContentsMargins(10,8,10,8); layout.setSpacing(4)
        layout.addWidget(lbl("[ HADI ]",OK_COL,make_font(bold=True,size=9)))
        if attachments:
            cr=QWidget(); cr.setStyleSheet(f"background:{BG};")
            crl=QHBoxLayout(cr); crl.setContentsMargins(0,0,0,0); crl.setSpacing(4)
            for a in attachments:
                icon={"image":"🖼","pdf":"📄","text":"📝"}.get(a["kind"],"📎")
                name=a["name"]
                if len(name)>22: name=name[:19]+"…"
                chip=QLabel(f"{icon} {name}"); chip.setFont(make_font(size=8))
                chip.setStyleSheet(f"color:{ACCENT};background:{ACCDIM};padding:2px 6px;border-radius:3px;")
                crl.addWidget(chip)
            crl.addStretch(); layout.addWidget(cr)
        if text: layout.addWidget(MessageBubble(text=text,bg=USER_BG,fg=OK_COL))

# ── System message ────────────────────────────────────────────────────────────
class SystemMessage(QWidget):
    def __init__(self,text,color=OK_COL,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG};")
        layout=QHBoxLayout(self); layout.setContentsMargins(10,4,10,4)
        l=QLabel(text); l.setFont(make_font(size=9)); l.setWordWrap(True)
        l.setStyleSheet(f"color:{color};background:transparent;padding:6px 10px;"
                        f"border-left:2px solid {color};")
        layout.addWidget(l); layout.addStretch()

# ── Boot widget ───────────────────────────────────────────────────────────────
class BootWidget(QWidget):
    boot_done = pyqtSignal()
    LINES = [
        ("◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈", ACCENT),
        ("  J.A.R.V.I.S  v4.1 BY OLLAMA AND ANTHROPIC", TEXT),
        ("  Just A Rather Very Intelligent System", TEXT),
        ("◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈", ACCENT),
        ("", TEXT),
        ("  > INITIALIZING NEURONS........", OK_COL),
        ("  > LOADING ALL MODLES.......", OK_COL),
        ("  > CALIBRATING RESPONSE STYLE......", OK_COL),
        ("", TEXT),
        ("  [ WAITING FOR SYSTEM CONFIRMATION ]", WARN),
    ]

    def __init__(self, parent=None, tts_voice=None, tts_on=True):
        super().__init__(parent)
        self._tts_voice        = tts_voice
        self._tts_on           = tts_on
        self._default_interval = 18

        # Prebake state: maps line_idx → duration_ms once synthesized
        self._prebaked_durations = {}
        # Which > lines exist (by index in LINES)
        self._spoken_indices = [i for i,(txt,_) in enumerate(self.LINES) if txt.strip().startswith(">")]
        self._prebake_done   = threading.Event()

        self.setStyleSheet(f"background:{BG};")
        layout = QVBoxLayout(self); layout.setContentsMargins(20,40,20,20); layout.setSpacing(0)
        self._labels = []
        for text, color in self.LINES:
            l = QLabel(""); l.setFont(make_font())
            l.setStyleSheet(f"color:{color};background:transparent;padding:1px 0;")
            layout.addWidget(l); self._labels.append((l, text, color))
        layout.addStretch()

        self._ollama_ready  = False
        self._line_idx      = 0
        self._char_idx      = 0
        self._dot_count     = 0
        self._line_started  = False
        self._type_timer    = QTimer(self); self._type_timer.timeout.connect(self._type_step)
        self._dot_timer     = QTimer(self); self._dot_timer.timeout.connect(self._pulse_dots)

        self._filler_labels = []
        for _ in range(20):
            fl = QLabel(""); fl.setFont(make_font())
            fl.setStyleSheet(f"color:{OK_COL};background:transparent;padding:1px 0;")
            layout.insertWidget(layout.count()-1, fl)
            self._filler_labels.append(fl)

        if tts_on:
            self._matrix_timer = QTimer(self)
            self._matrix_timer.timeout.connect(self._matrix_step)
            self._matrix_timer.start(150)
            threading.Thread(target=self._prebake_all, daemon=True).start()
        else:
            self._type_timer.start(self._default_interval)

    _MATRIX_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*><[]{}|◈▌░▒▓"

    def _matrix_step(self):
        import random
        chars = self._MATRIX_CHARS
        all_labels = [(l, full) for l, full, color in self._labels] +                      [(fl, "") for fl in self._filler_labels]
        for l, full in all_labels:
            length = len(full) if full else random.randint(20, 40)
            rand_text = "".join(random.choice(chars) for _ in range(length))
            l.setText(rand_text)
            l.setStyleSheet(f"color:{OK_COL};background:transparent;padding:1px 0;")

    def _prebake_all(self):
        """Background: wait for TTS ready, prebake all spoken lines, then start animation."""
        for _ in range(300):
            if _tts and _tts.is_ready(): break
            time.sleep(0.1)
        if not (_tts and _tts.is_ready()):
            # TTS failed — start without audio
            QTimer.singleShot(0, self._start_animation)
            return
        # Request prebake for each spoken line
        for idx in self._spoken_indices:
            txt, _ = self.LINES[idx]
            spoken = txt.strip().lstrip(">").strip().rstrip(".").strip()
            if spoken:
                _tts.prebake(idx, spoken, self._tts_voice)
        # Wait until all prebakes are confirmed (prebake_cb sets _prebaked_durations)
        deadline = time.time() + 30
        while time.time() < deadline:
            if len(self._prebaked_durations) >= len(self._spoken_indices):
                break
            time.sleep(0.05)
        QTimer.singleShot(0, self._start_animation)

    def on_prebaked(self, item_id, duration_ms):
        """Called from MainWindow when worker confirms a prebake is ready."""
        self._prebaked_durations[item_id] = duration_ms

    def _start_animation(self):
        self._matrix_timer.stop()
        for fl in self._filler_labels:
            fl.hide()
        for l, full, color in self._labels:
            l.setText("")
            l.setStyleSheet(f"color:{color};background:transparent;padding:1px 0;")
        self._type_timer.start(self._default_interval)

    def set_ollama_ready(self): self._ollama_ready = True

    def _type_step(self):
        if self._line_idx >= len(self.LINES):
            self._type_timer.stop(); self._dot_timer.start(400); return
        l, full, color = self._labels[self._line_idx]
        if not full:
            self._line_idx += 1; self._char_idx = 0; self._line_started = False; return
        if not self._line_started:
            self._line_started = True
            stripped = full.strip()
            if stripped.startswith(">") and self._tts_on and _tts:
                duration_ms = self._prebaked_durations.get(self._line_idx, 0)
                if duration_ms > 0:
                    # Start audio and sync typing speed to audio duration
                    _tts.play_prebaked(self._line_idx)
                    interval = max(8, duration_ms // max(len(full), 1))
                    self._type_timer.setInterval(interval)
                else:
                    self._type_timer.setInterval(self._default_interval)
            else:
                self._type_timer.setInterval(self._default_interval)
        if self._char_idx <= len(full):
            cur = "▌" if self._char_idx < len(full) else ""
            l.setText(full[:self._char_idx] + cur); self._char_idx += 1
        else:
            l.setText(full)
            self._line_idx += 1; self._char_idx = 0; self._line_started = False
            self._type_timer.setInterval(self._default_interval)

    def _pulse_dots(self):
        if self._ollama_ready:
            self._dot_timer.stop()
            l, _, _ = self._labels[-1]
            l.setText("  [ ◉  ALL SYSTEMS ONLINE ]")
            l.setStyleSheet(f"color:{OK_COL};background:transparent;padding:1px 0;")
            QTimer.singleShot(800, self.boot_done.emit)
        else:
            self._dot_count = (self._dot_count + 1) % 4
            dots = "." * self._dot_count + " " * (3 - self._dot_count)
            l, _, _ = self._labels[-1]; l.setText(f"  [ WAITING{dots} ]")

# ── History dialog ────────────────────────────────────────────────────────────
class HistoryDialog(QDialog):
    load_requested=pyqtSignal(str); new_requested=pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.Dialog)
        self.setFixedSize(380,500); self.setStyleSheet(f"background:{TITLEBAR};")
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        hdr=QWidget(); hdr.setFixedHeight(40); hdr.setStyleSheet(f"background:{CTRLBAR};")
        hl=QHBoxLayout(hdr); hl.setContentsMargins(12,0,8,0)
        hl.addWidget(lbl("[ CONVERSATION HISTORY ]",ACCENT,make_font(bold=True,size=9))); hl.addStretch()
        cls=QPushButton("×"); cls.setFixedSize(32,40)
        cls.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXTMUT};border:none;}}"
                          f"QPushButton:hover{{color:{ERR};}}")
        cls.clicked.connect(self.close); hl.addWidget(cls)
        layout.addWidget(hdr); layout.addWidget(hline())
        new_btn=QPushButton("[ + NEW CONVERSATION ]"); new_btn.setFont(make_font(bold=True,size=9))
        new_btn.setStyleSheet(f"QPushButton{{background:{ACCDIM};color:{ACCENT};border:none;padding:9px;}}"
                              f"QPushButton:hover{{background:{ACCENT};color:#000;}}")
        new_btn.clicked.connect(lambda:(self.new_requested.emit(),self.close()))
        layout.addWidget(new_btn); layout.addWidget(hline(BORDER))
        self._sc=QScrollArea(); self._sc.setWidgetResizable(True)
        self._sc.setStyleSheet(f"QScrollArea{{background:{BG};border:none;}}"
                               f"QScrollBar:vertical{{background:{BG};width:4px;}}"
                               f"QScrollBar::handle:vertical{{background:{ACCDIM};border-radius:2px;}}")
        self._inner=QWidget(); self._inner.setStyleSheet(f"background:{BG};")
        self._il=QVBoxLayout(self._inner); self._il.setContentsMargins(0,0,0,0); self._il.setSpacing(0)
        self._sc.setWidget(self._inner); layout.addWidget(self._sc,1)
        self._populate()

    def _populate(self):
        while self._il.count():
            item=self._il.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for c in list_convs(): self._add_row(c)
        self._il.addStretch()

    def _add_row(self,c):
        row=QWidget(); row.setStyleSheet(f"background:{BG};"); row.setFixedHeight(52)
        rl=QHBoxLayout(row); rl.setContentsMargins(12,4,8,4); rl.setSpacing(6)
        info=QWidget(); info.setStyleSheet("background:transparent;")
        il=QVBoxLayout(info); il.setContentsMargins(0,0,0,0); il.setSpacing(1)
        title=c.get("title","Untitled")
        if len(title)>34: title=title[:31]+"…"
        tl=QLabel(title); tl.setFont(make_font(bold=True,size=9))
        tl.setStyleSheet(f"color:{TEXT};background:transparent;")
        updated=c.get("updated","")[:16].replace("T"," ")
        dl=QLabel(updated); dl.setFont(make_font(size=7))
        dl.setStyleSheet(f"color:{TEXTMUT};background:transparent;")
        il.addWidget(tl); il.addWidget(dl); rl.addWidget(info,1)
        cid=c["id"]
        load_btn=QPushButton("[ OPEN ]"); load_btn.setFont(make_font(size=8))
        load_btn.setStyleSheet(f"QPushButton{{background:{ACCDIM};color:{ACCENT};border:none;padding:4px 8px;}}"
                               f"QPushButton:hover{{background:{ACCENT};color:#000;}}")
        load_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        load_btn.clicked.connect(lambda _,i=cid:(self.load_requested.emit(i),self.close()))
        rl.addWidget(load_btn)
        del_btn=QPushButton("[ × ]"); del_btn.setFont(make_font(size=8))
        del_btn.setStyleSheet(f"QPushButton{{background:#2a0808;color:{ERR};border:none;padding:4px 6px;}}"
                              f"QPushButton:hover{{background:#501010;}}")
        del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        del_btn.clicked.connect(lambda _,i=cid,w=row:self._delete(i,w))
        rl.addWidget(del_btn)
        self._il.addWidget(row); self._il.addWidget(hline(BORDER))

    def _delete(self,cid,row_widget):
        delete_conv(cid); row_widget.setParent(None); row_widget.deleteLater()

# ── Memory dialog ─────────────────────────────────────────────────────────────
class MemoryDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.Dialog)
        self.setFixedSize(360,400); self.setStyleSheet(f"background:{TITLEBAR};")
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        hdr=QWidget(); hdr.setFixedHeight(40); hdr.setStyleSheet(f"background:{CTRLBAR};")
        hl=QHBoxLayout(hdr); hl.setContentsMargins(12,0,8,0)
        hl.addWidget(lbl("[ MEMORY ]",ACCENT,make_font(bold=True,size=9))); hl.addStretch()
        cls=QPushButton("×"); cls.setFixedSize(32,40)
        cls.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXTMUT};border:none;}}"
                          f"QPushButton:hover{{color:{ERR};}}")
        cls.clicked.connect(self.close); hl.addWidget(cls)
        layout.addWidget(hdr); layout.addWidget(hline())
        mem=load_memory(); facts=mem.get("facts",[])
        sc=QScrollArea(); sc.setWidgetResizable(True)
        sc.setStyleSheet(f"QScrollArea{{background:{BG};border:none;}}")
        inner=QWidget(); inner.setStyleSheet(f"background:{BG};")
        il=QVBoxLayout(inner); il.setContentsMargins(12,12,12,12); il.setSpacing(6)
        if facts:
            for f in facts:
                fl=QLabel(f"• {f}"); fl.setFont(make_font(size=9))
                fl.setWordWrap(True); fl.setStyleSheet(f"color:{TEXT};background:transparent;")
                il.addWidget(fl)
        else:
            il.addWidget(lbl("No memories yet. Use /remember to save facts.",TEXTMUT,make_font(size=9)))
        il.addStretch(); sc.setWidget(inner); layout.addWidget(sc,1)
        clr=QPushButton("[ CLEAR ALL MEMORY ]"); clr.setFont(make_font(size=8))
        clr.setStyleSheet(f"QPushButton{{background:#2a0808;color:{ERR};border:none;padding:8px;}}"
                          f"QPushButton:hover{{background:#4a1010;}}")
        clr.clicked.connect(lambda:(save_memory({"facts":[]}),self.close()))
        layout.addWidget(clr)

# ── Main Window ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    _sig_chunk      = pyqtSignal(str)
    _sig_think      = pyqtSignal(str)
    _sig_sentence   = pyqtSignal(str)
    _sig_stats      = pyqtSignal(float,int,float)
    _sig_stream_done= pyqtSignal(str,bool)
    _sig_ollama_done= pyqtSignal(bool,str)
    _sig_stt_done   = pyqtSignal(str)
    _sig_stt_error  = pyqtSignal(str)
    _sig_status     = pyqtSignal(str,str)
    _sig_greet_ready = pyqtSignal()            # start greeting typewriter
    _sig_prebaked    = pyqtSignal(int, int)    # (id, duration_ms) prebake ready
    _sig_unleash     = pyqtSignal(str)         # flush buffered text + start voice
    _sig_toggle_win  = pyqtSignal()            # raise/minimize window from hotkey thread

    def __init__(self):
        super().__init__()
        self.history=[]; self.busy=False
        self.provider=DEFAULT_PROVIDER; self.think_on=True
        self.auto_scroll=True; self.stay_on_top=False
        self.tts_on=True; self.tts_voice="MALE"
        self._stop_evt=threading.Event()
        self._current_ai=None; self._attachments=[]
        self._conv_id=str(uuid.uuid4())
        self._memory=load_memory()
        self._recording=False; self._audio_frames=[]; self._right_alt_down=False
        self._transcribing=False
        self._input_locked=False
        self._hotkey_thread=None

        sett=load_settings()
        self.provider   =sett.get("provider",DEFAULT_PROVIDER)
        self.think_on   =sett.get("think_on",True)
        self.auto_scroll=sett.get("auto_scroll",True)
        self.stay_on_top=sett.get("stay_on_top",False)
        self.tts_on     =sett.get("tts_on",True)
        _saved_voice    =sett.get("tts_voice","MALE")
        self.tts_voice  =_saved_voice if _saved_voice in VOICES else "MALE"

        # Always start a fresh conversation on launch

        flags=Qt.WindowType.FramelessWindowHint
        if self.stay_on_top: flags|=Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WIN_W,WIN_H)
        screen=QApplication.primaryScreen().geometry()
        self.move(screen.width()-WIN_W-10,+10)

        self._build_ui()
        self._lock_input()   # locked until boot + greeting animation complete

        # TTS
        global _tts
        def _tts_status(msg, level="warn"):
            color = {"ok":OK_COL,"warn":WARN,"err":ERR}.get(level, WARN)
            self._sig_status.emit(msg, color)
        def _tts_prebake_cb(item_id, duration_ms):
            self._sig_prebaked.emit(item_id, duration_ms)
        _tts = TTSEngine(status_cb=_tts_status, prebake_cb=_tts_prebake_cb)
        _tts.set_voice(self.tts_voice)

        # STT subprocess (isolated process — avoids ctranslate2/Qt DLL conflict)
        global _stt_proc
        def _stt_status(msg, level="warn"):
            color={"ok":OK_COL,"warn":WARN,"err":ERR}.get(level,WARN)
            self._sig_status.emit(msg,color)
        _stt_proc = STTProcess(status_cb=_stt_status)

        self._sig_toggle_win.connect(self._toggle_window)
        self._sig_greet_ready.connect(self._on_greet_ready)
        self._sig_prebaked.connect(self._on_prebaked)
        self._sig_unleash.connect(self._on_unleash)
        self._sig_chunk.connect(self._on_chunk)
        self._sig_think.connect(self._on_think)
        self._sig_sentence.connect(self._on_sentence)
        self._sig_stats.connect(self._on_stats)
        self._sig_stream_done.connect(self._on_stream_done)
        self._sig_ollama_done.connect(self._on_ollama_done)
        self._sig_stt_done.connect(self._on_stt_done)
        self._sig_stt_error.connect(self._on_stt_error)
        self._sig_status.connect(self._on_status)

        self._ollama_worker=OllamaInitWorker()
        self._ollama_worker.done.connect(self._sig_ollama_done)
        self._ollama_worker.start()

        self._ping_timer=QTimer(self); self._ping_timer.timeout.connect(self._ping)
        self._drag_pos=None

        self.model_combo.setCurrentText(self.provider)
        self._start_hotkey_listener()

    def _lock_input(self):
        """Lock all input controls during boot animation and greeting typewriter."""
        self._input_locked = True
        self.send_btn.setEnabled(False)
        self.att_btn.setEnabled(False)
        self.mic_btn.setEnabled(False)
        self.prompt.setReadOnly(True)
        self.prompt.setStyleSheet(
            f"QTextEdit{{background:{TEXTAREA};color:{TEXTMUT};border:none;padding:6px;}}")

    def _unlock_input(self):
        """Unlock all input controls once boot and greeting are fully done."""
        self._input_locked = False
        self.send_btn.setEnabled(True)
        self.att_btn.setEnabled(True)
        self.mic_btn.setEnabled(True)
        self.prompt.setReadOnly(False)
        self.prompt.setStyleSheet(
            f"QTextEdit{{background:{TEXTAREA};color:{OK_COL};border:none;padding:6px;}}")

    def closeEvent(self,e):
        if self.history: save_conv(self._conv_id,conv_title(self.history),self.history)
        sett=load_settings()
        sett.update({"provider":self.provider,"think_on":self.think_on,
                     "auto_scroll":self.auto_scroll,"stay_on_top":self.stay_on_top,
                     "tts_on":self.tts_on,"tts_voice":self.tts_voice,
                     "last_conv_id":self._conv_id})
        save_settings(sett)
        if _tts: _tts.stop()
        # Stop keyboard hotkey
        try:
            import keyboard
            keyboard.unhook_all()
        except: pass
        super().closeEvent(e)

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        root=QWidget(); root.setObjectName("root")
        root.setStyleSheet(f"#root{{background:{BG};opacity:0.9;}}")
        self.setCentralWidget(root)
        main=QVBoxLayout(root); main.setContentsMargins(0,0,0,0); main.setSpacing(0)

        # ── Title bar
        tb=QWidget(); tb.setFixedHeight(44); tb.setStyleSheet(f"background:{TITLEBAR};")
        tbl=QHBoxLayout(tb); tbl.setContentsMargins(14,0,4,0); tbl.setSpacing(0)
        title=QLabel("J.A.R.V.I.S"); title.setFont(make_font(bold=True,size=12))
        title.setStyleSheet(f"color:{ACCENT};background:transparent;")
        tbl.addWidget(title); tbl.addStretch()
        for text,tip,cb,hover in [
            ("[ MEM ]","Memory",self._show_memory,CLAUDE_COL),
            ("[ HIST ]","History",self._show_history,ACCENT),
        ]:
            b=QPushButton(text); b.setFont(make_font(bold=True,size=8))
            b.setFixedHeight(44); b.setToolTip(tip)
            b.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXTMUT};border:none;padding:0 8px;}}"
                            f"QPushButton:hover{{color:{hover};}}")
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.clicked.connect(cb); tbl.addWidget(b)
        for text,tip,slot,hover in [("[ — ]","Minimize",self.showMinimized,ACCDIM),
                                     ("[ × ]","Close",self.close,"#4a1010")]:
            b=QPushButton(text); b.setFont(make_font(bold=True,size=9))
            b.setFixedSize(46,44); b.setToolTip(tip)
            b.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXTMUT};border:none;}}"
                            f"QPushButton:hover{{background:{hover};color:white;}}")
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.clicked.connect(slot); tbl.addWidget(b)
        main.addWidget(tb)

        # ── Controls bar — model combo + ⚙ settings button
        cb=QWidget(); cb.setFixedHeight(34); cb.setStyleSheet(f"background:{CTRLBAR};")
        cbl=QHBoxLayout(cb); cbl.setContentsMargins(10,0,10,0); cbl.setSpacing(8)

        cbl.addWidget(lbl("model:",TEXTMUT,make_font(size=8)))
        self.model_combo=QComboBox(); self.model_combo.addItems(PROVIDERS.keys())
        self.model_combo.setFont(make_font(bold=True,size=8))
        self.model_combo.setStyleSheet(COMBO_SS(ACCENT))
        self.model_combo.currentTextChanged.connect(self._set_provider)
        cbl.addWidget(self.model_combo)

        cbl.addStretch()

        # ⚙ settings button — opens QMenu dropdown
        self.settings_btn=QPushButton("⚙"); self.settings_btn.setFont(make_font(bold=True,size=11))
        self.settings_btn.setFixedSize(34,26)
        self.settings_btn.setStyleSheet(
            f"QPushButton{{background:#000d14;color:{ACCENT};border:1px solid {ACCDIM};padding:0;}}"
            f"QPushButton:hover{{border-color:{ACCENT};}}"
        )
        self.settings_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.settings_btn.clicked.connect(self._show_settings_menu)
        cbl.addWidget(self.settings_btn)
        main.addWidget(cb)

        # ── Stats bar
        main.addWidget(hline())
        sb=QWidget(); sb.setFixedHeight(20); sb.setStyleSheet(f"background:{TITLEBAR};")
        sbl=QHBoxLayout(sb); sbl.setContentsMargins(8,0,8,0); sbl.setSpacing(4)
        self.s_tps=QLabel("—"); self.s_tok=QLabel("—"); self.s_time=QLabel("—")
        for lt,vl in [("t/s:",self.s_tps),("tok:",self.s_tok),("time:",self.s_time)]:
            sbl.addWidget(lbl(lt,TEXTDIM,make_font("Courier New",8)))
            vl.setFont(make_font("Courier New",8)); vl.setStyleSheet(f"color:{STATFG};background:transparent;")
            sbl.addWidget(vl); sbl.addSpacing(6)
        sbl.addStretch()
        self.status_lbl=QLabel("◉  CONNECTING"); self.status_lbl.setFont(make_font("Courier New",8))
        self.status_lbl.setStyleSheet(f"color:{WARN};background:transparent;"); sbl.addWidget(self.status_lbl)
        main.addWidget(sb); main.addWidget(hline())

        # ── Chat feed
        self.scroll=QScrollArea(); self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"""
            QScrollArea{{background:{BG};border:none;}}
            QScrollBar:vertical{{background:{BG};width:4px;margin:0;}}
            QScrollBar::handle:vertical{{background:{ACCDIM};border-radius:2px;min-height:20px;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}
        """)
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)
        self.feed_widget=QWidget(); self.feed_widget.setStyleSheet(f"background:{BG};")
        self.feed_layout=QVBoxLayout(self.feed_widget)
        self.feed_layout.setContentsMargins(0,0,0,0); self.feed_layout.setSpacing(0)
        self.feed_layout.addStretch()
        self.scroll.setWidget(self.feed_widget); main.addWidget(self.scroll,1)
        self.boot_widget=BootWidget(
            tts_voice=self.tts_voice,
            tts_on=self.tts_on,
        )
        self.boot_widget.boot_done.connect(self._show_greeting)
        self.feed_layout.insertWidget(0,self.boot_widget)

        # ── Input area
        main.addWidget(hline())
        ia=QWidget(); ia.setStyleSheet(f"background:{INPUT_BG};")
        ial=QVBoxLayout(ia); ial.setContentsMargins(10,8,10,8); ial.setSpacing(4)
        self.chips_widget=QWidget(); self.chips_widget.setStyleSheet(f"background:{INPUT_BG};")
        self.chips_layout=QHBoxLayout(self.chips_widget)
        self.chips_layout.setContentsMargins(0,0,0,0); self.chips_layout.setSpacing(4)
        self.chips_layout.addStretch(); self.chips_widget.setVisible(False)
        ial.addWidget(self.chips_widget)
        self.prompt=PromptBox()
        self.prompt.setPlaceholderText("Enter message… /remember <fact>")
        self.prompt.installEventFilter(self); ial.addWidget(self.prompt)

        br=QWidget(); br.setStyleSheet(f"background:{INPUT_BG};")
        brl=QHBoxLayout(br); brl.setContentsMargins(0,0,0,0); brl.setSpacing(6)

        self.mic_btn=QPushButton("[ REC ]"); self.mic_btn.setFont(make_font(bold=True,size=9))
        self.mic_btn.setStyleSheet(f"QPushButton{{background:{TEXTAREA};color:{ACCENT};border:none;padding:6px 10px;}}"
                                   f"QPushButton:hover{{background:{ACCDIM};}}")
        self.mic_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.mic_btn.setToolTip("Hold Right Alt or click to record")
        self.mic_btn.pressed.connect(self._start_recording)
        self.mic_btn.released.connect(self._stop_recording)
        brl.addWidget(self.mic_btn)

        self.att_btn=QPushButton("[ + ]"); self.att_btn.setFont(make_font(bold=True,size=9))
        self.att_btn.setStyleSheet(f"QPushButton{{background:{TEXTAREA};color:{ACCENT};border:none;padding:6px 12px;}}"
                              f"QPushButton:hover{{background:{ACCDIM};}}")
        self.att_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.att_btn.setToolTip("Attach file"); self.att_btn.clicked.connect(self._attach_file)
        brl.addWidget(self.att_btn)

        self.send_btn=QPushButton("[ TRANSMIT ]"); self.send_btn.setFont(make_font(bold=True,size=9))
        self.send_btn.setStyleSheet(f"QPushButton{{background:{ACCENT};color:#000;border:none;padding:6px 16px;}}"
                                    f"QPushButton:hover{{background:#00eeff;}}"
                                    f"QPushButton:disabled{{background:{ACCDIM};color:{TEXTMUT};}}")
        self.send_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.send_btn.clicked.connect(self.send); brl.addWidget(self.send_btn,1)

        self.abort_btn=QPushButton("[ ABORT ]"); self.abort_btn.setFont(make_font(bold=True,size=9))
        self.abort_btn.setStyleSheet(f"QPushButton{{background:#3a0a0a;color:{ERR};border:none;padding:6px 12px;}}"
                                     f"QPushButton:hover{{background:#501010;color:white;}}"
                                     f"QPushButton:disabled{{background:#1a0505;color:#3a1a1a;}}")
        self.abort_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.abort_btn.setEnabled(False); self.abort_btn.clicked.connect(self._abort)
        brl.addWidget(self.abort_btn)
        ial.addWidget(br); main.addWidget(ia)

    # ── Settings menu ─────────────────────────────────────────────────────────
    def _show_settings_menu(self):
        menu=QMenu(self); menu.setStyleSheet(MENU_SS)
        is_claude=PROVIDERS[self.provider]["type"]=="anthropic"

        a1=menu.addAction(f"TTS:     {'ON ✓' if self.tts_on else 'OFF'}")
        a1.setFont(make_font(size=9))

        a2=menu.addAction(f"VOICE:   {self.tts_voice}")
        a2.setFont(make_font(size=9))

        menu.addSeparator()

        a3=menu.addAction(f"SCROLL:  {'ON ✓' if self.auto_scroll else 'OFF'}")
        a3.setFont(make_font(size=9))

        think_label=f"THINK:   {'N/A' if is_claude else ('ON ✓' if self.think_on else 'OFF')}"
        a4=menu.addAction(think_label)
        a4.setFont(make_font(size=9))
        if is_claude: a4.setEnabled(False)

        a5=menu.addAction(f"ON TOP:  {'ON ✓' if self.stay_on_top else 'OFF'}")
        a5.setFont(make_font(size=9))

        # Show menu below the ⚙ button
        pos=self.settings_btn.mapToGlobal(
            QPoint(0, self.settings_btn.height()))
        chosen=menu.exec(pos)

        if chosen==a1:
            # Lock TTS toggle during boot, greeting, or active response
            locked = self.boot_widget is not None or                      (hasattr(self,'_greet_timer') and self._greet_timer and self._greet_timer.isActive()) or                      self.busy
            if not locked:
                self.tts_on = not self.tts_on
                if not self.tts_on and _tts: _tts.stop()
        elif chosen==a2:
            locked = self.boot_widget is not None or                      (hasattr(self,'_greet_timer') and self._greet_timer and self._greet_timer.isActive()) or                      self.busy
            if not locked:
                self.tts_voice = "FEMALE" if self.tts_voice=="MALE" else "MALE"
                if _tts: _tts.set_voice(self.tts_voice)
        elif chosen==a3:
            self.auto_scroll=not self.auto_scroll
        elif chosen==a4:
            if not is_claude: self.think_on=not self.think_on
        elif chosen==a5:
            self._toggle_top()

    # ── Top button ────────────────────────────────────────────────────────────
    def _toggle_top(self):
        self.stay_on_top=not self.stay_on_top
        flags=Qt.WindowType.FramelessWindowHint
        if self.stay_on_top: flags|=Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags); self.show()

    def _on_scroll_changed(self,val):
        sb=self.scroll.verticalScrollBar()
        if val<sb.maximum()-20 and self.busy:
            if self.auto_scroll: self.auto_scroll=False

    # ── Status ────────────────────────────────────────────────────────────────
    def _on_status(self,msg,color):
        self.status_lbl.setText(msg)
        self.status_lbl.setStyleSheet(f"color:{color};background:transparent;")

    # ── Ollama ────────────────────────────────────────────────────────────────
    def _on_ollama_done(self,ok,msg):
        if self.boot_widget: self.boot_widget.set_ollama_ready()
        col=OK_COL if ok else ERR; txt="◉  ONLINE" if ok else "◉  OFFLINE"
        self.status_lbl.setText(txt)
        self.status_lbl.setStyleSheet(f"color:{col};background:transparent;")
        if ok: self._ping_timer.start(10000)

    def _check_ollama(self):
        up=tcp_up(2); col=OK_COL if up else ERR; txt="◉  ONLINE" if up else "◉  OFFLINE"
        self.status_lbl.setText(txt)
        self.status_lbl.setStyleSheet(f"color:{col};background:transparent;")

    def _ping(self):
        if PROVIDERS[self.provider]["type"]=="ollama":
            threading.Thread(target=self._check_ollama,daemon=True).start()

    # ── Provider ──────────────────────────────────────────────────────────────
    def _set_provider(self,name):
        self.provider=name
        is_claude=PROVIDERS[name]["type"]=="anthropic"
        col=CLAUDE_COL if is_claude else ACCENT
        self.model_combo.setStyleSheet(COMBO_SS(col))
        if is_claude:
            key=ANTHROPIC_API_KEY.strip()
            if not key or key=="YOUR_API_KEY_HERE":
                self.status_lbl.setText("⚠  NO API KEY")
                self.status_lbl.setStyleSheet(f"color:{ERR};background:transparent;")
            else:
                self.status_lbl.setText(f"◈  {name}")
                self.status_lbl.setStyleSheet(f"color:{CLAUDE_COL};background:transparent;")
        else:
            threading.Thread(target=self._check_ollama,daemon=True).start()

    # ── Boot → greeting ───────────────────────────────────────────────────────
    def _on_prebaked(self, item_id, duration_ms):
        """Called on main thread when a prebake is ready. Route to boot, greeting, or response."""
        if item_id == -1:
            # Greeting
            self._greet_duration = duration_ms
            self._sig_greet_ready.emit()
        elif item_id == 100:
            # First response sentence — unleash display and audio together
            self._sig_unleash.emit(self._chunk_buffer)
        elif self.boot_widget is not None:
            # Boot lines
            self.boot_widget.on_prebaked(item_id, duration_ms)

    def _show_greeting(self):
        self.boot_widget.deleteLater(); self.boot_widget = None
        if self.history: self._rebuild_feed(); self._unlock_input(); return
        msg = AIMessage(show_think=False)
        self.feed_layout.insertWidget(self.feed_layout.count()-1, msg)
        self._start_greeting(msg)

    def _start_greeting(self, msg):
        """Prebake greeting audio while showing throat-clearing, then start typing+audio together."""
        if hasattr(self, '_greet_timer') and self._greet_timer:
            try: self._greet_timer.stop()
            except: pass
        self._greet_text     = GREETING_TEXT
        self._greet_idx      = 0
        self._greet_msg      = msg
        self._greet_duration = 0

        if self.tts_on and _tts and _tts.is_ready():
            # Show throat clearing while prebaking
            msg.start_throat_clearing()
            _tts.prebake(-1, GREETING_TEXT, self.tts_voice)
        else:
            msg.resp.setText("▌")
            self._sig_greet_ready.emit()

    def _on_greet_ready(self):
        """Called on main thread — audio is prebaked and ready. Start typing + playback together."""
        self._greet_msg.stop_throat_clearing()
        if self.tts_on and _tts and self._greet_duration > 0:
            _tts.play_prebaked(-1)
            interval = max(8, self._greet_duration // max(len(GREETING_TEXT), 1))
        else:
            interval = 22
        self._greet_timer = QTimer(self)
        self._greet_timer.timeout.connect(self._greet_step)
        self._greet_timer.start(interval)

    def _greet_step(self):
        if self._greet_idx <= len(self._greet_text):
            cur = "▌" if self._greet_idx < len(self._greet_text) else ""
            self._greet_msg.resp.setText(self._greet_text[:self._greet_idx] + cur)
            self._greet_idx += 1; self._scroll_bottom()
        else:
            self._greet_timer.stop()
            self._greet_msg.resp.setText(self._greet_text)
            self._unlock_input()

    # ── Feed ──────────────────────────────────────────────────────────────────
    def _scroll_bottom(self):
        if self.auto_scroll:
            QTimer.singleShot(0,lambda:self.scroll.verticalScrollBar().setValue(
                self.scroll.verticalScrollBar().maximum()))

    def _add_widget(self,w):
        self.feed_layout.insertWidget(self.feed_layout.count()-1,w)
        self._scroll_bottom()

    # ── Dialogs ───────────────────────────────────────────────────────────────
    def _show_history(self):
        dlg=HistoryDialog(self)
        dlg.load_requested.connect(self._load_conv)
        dlg.new_requested.connect(self._new_conv)
        dlg.move(self.x()-dlg.width()-10,self.y()+60); dlg.exec()

    def _show_memory(self):
        dlg=MemoryDialog(self)
        dlg.move(self.x()-dlg.width()-10,self.y()+60); dlg.exec()

    def _load_conv(self,cid):
        if self.history: save_conv(self._conv_id,conv_title(self.history),self.history)
        try:
            data=load_conv(cid)
            self.history=data.get("history",[]); self._conv_id=cid
            self._rebuild_feed()
        except Exception: pass

    def _new_conv(self):
        if self.history: save_conv(self._conv_id,conv_title(self.history),self.history)
        self.history=[]; self._conv_id=str(uuid.uuid4())
        self._lock_input()
        self._rebuild_feed(show_greeting=True)

    def _rebuild_feed(self,show_greeting=False):
        while self.feed_layout.count()>1:
            item=self.feed_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        if show_greeting:
            msg=AIMessage(show_think=False)
            self._add_widget(msg)
            self._start_greeting(msg)
        else:
            for m in self.history:
                role=m.get("role",""); content=m.get("content","")
                if role=="user":
                    if isinstance(content,list):
                        content="\n".join(c["text"] for c in content if c.get("type")=="text")
                    self._add_widget(UserMessage(str(content)))
                elif role=="assistant":
                    msg=AIMessage(show_think=False); msg.resp.setText(str(content))
                    self._add_widget(msg)
        self._scroll_bottom()

    # ── Drag ──────────────────────────────────────────────────────────────────
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:
            self._drag_pos=e.globalPosition().toPoint()-self.frameGeometry().topLeft()
    def mouseMoveEvent(self,e):
        if self._drag_pos and e.buttons()==Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint()-self._drag_pos)
    def mouseReleaseEvent(self,e): self._drag_pos=None

    # ── Enter key ─────────────────────────────────────────────────────────────
    def eventFilter(self,obj,e):
        from PyQt6.QtCore import QEvent
        if obj is self.prompt and e.type()==QEvent.Type.KeyPress:
            if e.key()==Qt.Key.Key_Return and not(e.modifiers()&Qt.KeyboardModifier.ShiftModifier):
                self.send(); return True
        return super().eventFilter(obj,e)

    # ── Attach ────────────────────────────────────────────────────────────────
    def _attach_file(self):
        paths,_=QFileDialog.getOpenFileNames(self,"Attach files","",
            "All supported (*.png *.jpg *.jpeg *.webp *.gif *.pdf *.txt *.py *.js "
            "*.ts *.html *.css *.md *.json *.csv *.xml *.yaml *.yml *.sh *.bat "
            "*.c *.cpp *.h *.java *.rs *.go *.rb *.php);;"
            "Images (*.png *.jpg *.jpeg *.webp *.gif);;"
            "PDF (*.pdf);;Text files (*.txt *.py *.js *.md *.json *.csv);;All files (*.*)")
        for path in paths:
            att=read_file(path)
            if att: self._attachments.append(att); self._add_chip(att)

    def _add_chip(self,att):
        chip=AttachChip(att); chip.removed.connect(self._remove_chip)
        self.chips_layout.insertWidget(self.chips_layout.count()-1,chip)
        self.chips_widget.setVisible(True)

    def _remove_chip(self,chip):
        self._attachments=[a for a in self._attachments if a is not chip.attachment]
        chip.setParent(None); chip.deleteLater()
        if not self._attachments: self.chips_widget.setVisible(False)

    # ── STT ───────────────────────────────────────────────────────────────────
    def _start_hotkey_listener(self):
        def _handle(e):
            if e.name != "right alt": return
            if e.event_type == "down" and not self._right_alt_down:
                self._right_alt_down = True
                self._hotkey_press()
            elif e.event_type == "up" and self._right_alt_down:
                self._right_alt_down = False
                self._hotkey_release()

        def _listen():
            try:
                import keyboard
                keyboard.hook(_handle)
                keyboard.add_hotkey("esc", lambda: _tts.stop() if _tts else None, suppress=False)
                keyboard.add_hotkey("ctrl+alt+j", lambda: self._sig_toggle_win.emit(), suppress=False)
                keyboard.wait()
            except Exception as e:
                print(f"[STT] keyboard hotkey failed: {e}")
        self._hotkey_thread=threading.Thread(target=_listen,daemon=True)
        self._hotkey_thread.start()

    def _hotkey_press(self):
        if self._input_locked: return
        if not self._recording and not self._transcribing:
            self._sig_stt_done.emit("__START__")

    def _hotkey_release(self):
        if self._recording:
            self._sig_stt_done.emit("__STOP__")
    
    def _toggle_window(self):
        if self.isMinimized() or not self.isVisible():
            self.showNormal()
            self.activateWindow()
            self.raise_()
        else:
            self.showMinimized()

    def _set_mic_recording(self):
        self.mic_btn.setText("[ ● ]")
        self.mic_btn.setStyleSheet(
            f"QPushButton{{background:#3a0808;color:{ERR};border:none;padding:6px 10px;}}"
            f"QPushButton:hover{{background:#501010;}}")

    def _set_mic_idle(self):
        self.mic_btn.setText("[ REC ]")
        self.mic_btn.setStyleSheet(
            f"QPushButton{{background:{TEXTAREA};color:{ACCENT};border:none;padding:6px 10px;}}"
            f"QPushButton:hover{{background:{ACCDIM};}}")

    def _start_recording(self):
        if self._input_locked or self._recording or self._transcribing: return
        self._recording=True; self._audio_frames=[]
        self._set_mic_recording()
        self.prompt.set_stt_state("recording")
        threading.Thread(target=self._record_audio,daemon=True).start()

    def _stop_recording(self):
        if not self._recording: return
        self._recording=False
        self._set_mic_idle()
        if self._audio_frames:
            self._transcribing=True
            self.prompt.set_stt_state("transcribing")
            threading.Thread(target=self._transcribe,daemon=True).start()
        else:
            self.prompt.set_stt_state("idle")
            self.status_lbl.setText("◈  NO AUDIO")
            self.status_lbl.setStyleSheet(f"color:{WARN};background:transparent;")

    def _record_audio(self):
        try:
            import pyaudio
            p=pyaudio.PyAudio()
            stream=p.open(format=pyaudio.paInt16,channels=1,rate=16000,
                          input=True,frames_per_buffer=1024)
            print("[STT] Recording started")
            while self._recording:
                data=stream.read(1024,exception_on_overflow=False)
                self._audio_frames.append(data)
            stream.stop_stream(); stream.close(); p.terminate()
            print(f"[STT] Recording stopped — {len(self._audio_frames)} frames")
        except Exception as e:
            print(f"[STT] Recording error: {e}")
            self._sig_stt_error.emit(f"Mic error: {e}")

    def _transcribe(self):
        try:
            import numpy as np
            audio_bytes = b"".join(self._audio_frames)
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            print(f"[STT] Transcribing {len(audio_np)/16000:.1f}s of audio")
            text = _stt_proc.transcribe(audio_np)
            print(f"[STT] Result: '{text}'")
            self._sig_stt_done.emit(text if text else "")
        except Exception as e:
            print(f"[STT] Transcribe error: {e}")
            self._sig_stt_error.emit(str(e))

    def _on_stt_done(self,text):
        if text=="__START__": self._start_recording(); return
        if text=="__STOP__": self._stop_recording(); return
        self._transcribing=False
        if text:
            # Append transcribed text to whatever was in the box before recording
            combined = (self.prompt._saved_text + " " + text).strip()
            self.prompt._saved_text = combined
            self.status_lbl.setText("◈  STT DONE")
            self.status_lbl.setStyleSheet(f"color:{OK_COL};background:transparent;")
        else:
            self.status_lbl.setText("◈  NOTHING HEARD")
            self.status_lbl.setStyleSheet(f"color:{WARN};background:transparent;")
        self.prompt.set_stt_state("idle")

    def _on_stt_error(self,err):
        print(f"[STT] Error: {err}")
        self._transcribing=False
        self.prompt.set_stt_state("idle")
        self._sig_status.emit(f"⚠  STT: {err[:30]}", ERR)

    # ── TTS ───────────────────────────────────────────────────────────────────
    def _on_sentence(self, sentence):
        if not (self.tts_on and _tts and _tts.is_ready()): return
        clean = re.sub(r'[*_`#\[\]()]', '', sentence).replace('\n', ' ').strip()
        clean = re.sub(r' +', ' ', clean)  # collapse multiple spaces
        if not clean: return
        if not self._first_sentence_sent:
            # Prebake first sentence — _on_prebaked will unleash display + audio
            self._first_sentence_sent = True
            _tts.prebake(100, clean, self.tts_voice)
        else:
            _tts.speak(clean, self.tts_voice)

    # ── Send ──────────────────────────────────────────────────────────────────
    def send(self):
        if self.busy: return
        text=self.prompt.toPlainText().strip()
        attachments=list(self._attachments)
        if not text and not attachments: return

        if text.lower().startswith("/remember"):
            fact=text[9:].strip(); self.prompt.clear()
            if fact:
                facts=self._memory.get("facts",[])
                if fact not in facts:
                    facts.append(fact); self._memory["facts"]=facts; save_memory(self._memory)
                    self._add_widget(SystemMessage(f"◈  MEMORY SAVED: \"{fact}\"",OK_COL))
                else:
                    self._add_widget(SystemMessage(f"◈  ALREADY KNOWN: \"{fact}\"",WARN))
            else:
                self._add_widget(SystemMessage(
                    "◈  Usage: /remember <fact>  —  e.g. /remember My name is Hadi",WARN))
            return

        self.prompt.clear(); self._attachments.clear()
        for i in reversed(range(self.chips_layout.count()-1)):
            w=self.chips_layout.itemAt(i).widget()
            if w: w.setParent(None); w.deleteLater()
        self.chips_widget.setVisible(False)
        self._add_widget(UserMessage(text,attachments))

        prov=PROVIDERS[self.provider]; is_local=prov["type"]=="ollama"
        if attachments:
            hist_msg=(build_ollama_msg(text,attachments) if is_local
                      else build_anthropic_msg(text,attachments))
        else:
            hist_msg={"role":"user","content":text}
        self.history.append(hist_msg)

        mem_str=memory_prompt(self._memory)
        prov_info=f"\n\nCurrent model: {self.provider} ({prov['model']})"
        system_text=JARVIS_SYSTEM+prov_info+mem_str

        trimmed=self.history[-MAX_HISTORY:] if len(self.history)>MAX_HISTORY else self.history
        full_messages=(
            [{"role":"system","content":system_text}]+list(trimmed)
            if is_local else list(trimmed)
        )

        self.s_tps.setText("…"); self.s_tok.setText("…"); self.s_time.setText("…")
        self._stop_evt.clear(); self.busy = True
        self.send_btn.setEnabled(False); self.abort_btn.setEnabled(True)
        self.auto_scroll = True
        if _tts: _tts.stop()

        # TTS unleash state — holds text display until first sentence prebaked
        self._tts_unleashed = not (self.tts_on and _tts and _tts.is_ready())
        self._chunk_buffer  = ""
        self._first_sentence_sent = False

        show_think = self.think_on and is_local
        self._current_ai = AIMessage(show_think=show_think)
        self._add_widget(self._current_ai)
        if not self._tts_unleashed:
            self._current_ai.start_throat_clearing()

        self._worker=StreamWorker(prov,full_messages,system_text,show_think,self._stop_evt)
        self._worker.chunk.connect(self._sig_chunk)
        self._worker.think_chunk.connect(self._sig_think)
        self._worker.sentence.connect(self._sig_sentence)
        self._worker.stats.connect(self._sig_stats)
        self._worker.finished.connect(self._sig_stream_done)
        self._worker.start()

    def _abort(self):
        self._stop_evt.set()
        if _tts: _tts.stop()

    # ── Stream callbacks ──────────────────────────────────────────────────────
    def _on_chunk(self, text):
        if not self._current_ai: return
        if self.tts_on and not self._tts_unleashed:
            # Buffer chunks until first sentence prebake is ready
            self._chunk_buffer = text  # StreamWorker sends full accumulated text each chunk
            # Don't update display — throat clearing animation is showing
        else:
            self._current_ai.update_resp(text + " ▌")
            self._scroll_bottom()

    def _on_unleash(self, buffered_text):
        """First sentence prebaked — show all buffered text and start voice simultaneously."""
        if not self._current_ai: return
        self._tts_unleashed = True
        self._current_ai.stop_throat_clearing()
        if buffered_text:
            self._current_ai.update_resp(buffered_text + " ▌")
        self._scroll_bottom()
        # Play the prebaked first sentence
        if _tts: _tts.play_prebaked(100)

    def _on_think(self, text):
        if self._current_ai: self._current_ai.update_think(text); self._scroll_bottom()

    def _on_stats(self, tps, tok, elapsed):
        self.s_tps.setText(f"{tps:.1f}"); self.s_tok.setText(str(tok))
        self.s_time.setText(f"{elapsed:.1f}s")

    def _on_stream_done(self, text, aborted):
        if self._current_ai:
            # If TTS never unleashed (very short response or TTS off), show text now
            if not self._tts_unleashed and self._current_ai:
                self._current_ai.stop_throat_clearing()
            self._current_ai.finalize(text, aborted); self._scroll_bottom()
        self.abort_btn.setEnabled(False); self._current_ai = None
        self._tts_unleashed = True  # reset
        if not aborted:
            self.history.append({"role":"assistant","content":text})
            save_conv(self._conv_id, conv_title(self.history), self.history)
            for tag, arg in parse_commands(text):
                result = execute_pc_command(tag, arg, confirm_cb=self._confirm_destructive)
                if result:
                    self._add_widget(SystemMessage(f"◈  {result}", ACCENT))
        self.busy = False; self.send_btn.setEnabled(True)

    def _confirm_destructive(self, message):
        """Confirmation dialog for destructive commands like shutdown/restart."""
        from PyQt6.QtWidgets import QMessageBox
        dlg = QMessageBox(self)
        dlg.setWindowTitle("JARVIS — Confirm")
        dlg.setText(message)
        dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dlg.setDefaultButton(QMessageBox.StandardButton.No)
        dlg.setStyleSheet(f"background:{BG};color:{TEXT};")
        return dlg.exec() == QMessageBox.StandardButton.Yes


if __name__=="__main__":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("jarvis.app")
    app=QApplication(sys.argv); app.setStyle("Fusion")
    win=MainWindow(); win.show()
    win.setWindowIcon(QIcon("assets/jarvis.ico"))
    app.setWindowIcon(QIcon("assets/jarvis.ico"))
    sys.exit(app.exec())