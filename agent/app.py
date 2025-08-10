
import json, os, subprocess
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from itsdangerous import TimestampSigner, BadSignature

APP = FastAPI()
APP.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE = Path("/etc/infokiosk")
BASE.mkdir(parents=True, exist_ok=True)
CFG_PATH = BASE / "agent.json"
ENV_PATH = BASE / "agent.env"
ROTATOR = Path(__file__).parent / "rotator.html"

# bootstrap config
if not CFG_PATH.exists():
    default = json.loads((Path(__file__).parent / "config.default.json").read_text())
    CFG_PATH.write_text(json.dumps(default, indent=2))

def read_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith('#'): continue
            k,v = line.split('=',1)
            env[k.strip()]=v.strip()
    env.setdefault("AGENT_TOKEN", "please-change-me")
    env.setdefault("SECRET_KEY", "please-change-me")
    env.setdefault("AGENT_PORT", "8001")
    return env

ENV = read_env()
signer = TimestampSigner(ENV["SECRET_KEY"])
APP.add_middleware(SessionMiddleware, secret_key=ENV["SECRET_KEY"])

def require_bearer(request: Request):
    auth = request.headers.get("authorization","")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = auth.split(None,1)[1]
    if token != ENV["AGENT_TOKEN"]:
        raise HTTPException(403, "Invalid token")
    return True

def read_cfg():
    return json.loads(CFG_PATH.read_text())

def write_cfg(d):
    CFG_PATH.write_text(json.dumps(d, indent=2))

@APP.get("/api/health")
def health():
    cfg = read_cfg()
    return {"ok": True, "name": cfg.get("name"), "count": len(cfg.get("playlist", []))}

@APP.get("/api/playlist", response_class=JSONResponse)
def get_playlist():
    return read_cfg().get("playlist", [])

@APP.post("/api/playlist")
def set_playlist(request: Request):
    require_bearer(request)
    data = None
    try:
        data = request.json()
    except:
        data = None
    if data is None:
        data = []
    # validate
    playlist = []
    for item in data:
        url = str(item.get("url", "")).strip()
        timeout = int(item.get("timeout", 30))
        if url:
            playlist.append({"url": url, "timeout": max(5, timeout)})
    cfg = read_cfg()
    cfg["playlist"] = playlist
    write_cfg(cfg)
    return {"ok": True, "count": len(playlist)}

@APP.post("/api/reboot")
def reboot(request: Request):
    require_bearer(request)
    try:
        subprocess.Popen(["sudo", "/sbin/reboot"])
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))

@APP.get("/rotator", response_class=HTMLResponse)
def rotator():
    return HTMLResponse(ROTATOR.read_text())

# static mount (optional future assets)
static_dir = Path("/var/lib/infokiosk/static")
static_dir.mkdir(parents=True, exist_ok=True)
APP.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:APP", host="0.0.0.0", port=int(ENV["AGENT_PORT"]))
