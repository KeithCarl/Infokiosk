import os, json, requests
from pathlib import Path
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

BASE = Path("/etc/infokiosk")
ENV_PATH = BASE / "admin.env"
ADMIN_CFG = BASE / "admin.json"

def read_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith('#'): continue
            k,v = line.split('=',1)
            env[k.strip()]=v.strip()
    env.setdefault("ADMIN_PASSWORD", "changeme")
    env.setdefault("SECRET_KEY", "please-change-me")
    env.setdefault("AGENT_TOKEN", "please-change-me")
    env.setdefault("ADMIN_PORT", "8000")
    env.setdefault("KIOSK_PEERS", "Infopoint1.local,InfoPoint2.local")
    return env

ENV = read_env()
APP = FastAPI()
APP.add_middleware(SessionMiddleware, secret_key=ENV["SECRET_KEY"])
TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
APP.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

def logged_in(request: Request):
    return request.session.get("auth", False) is True

def require_auth(request: Request):
    if not logged_in(request):
        raise HTTPException(401, "Not logged in")

def peers():
    # Admin UI treats peers as mapping name->host
    cfg = {"peers": {}}
    if ADMIN_CFG.exists():
        try:
            cfg.update(json.loads(ADMIN_CFG.read_text()))
        except:
            pass
    if not cfg["peers"]:
        # derive from env list; assume .local hostnames map to themselves
        for host in [p.strip() for p in ENV["KIOSK_PEERS"].split(",") if p.strip()]:
            name = host.split(".")[0]
            cfg["peers"][name] = host
    return cfg["peers"]

def agent_url(host, path):
    return f"http://{host}:8001{path}"

def agent_headers():
    return {"Authorization": f"Bearer {ENV['AGENT_TOKEN']}"}

@APP.get("/", response_class=HTMLResponse)
def index(request: Request):
    if not logged_in(request):
        return TEMPLATES.TemplateResponse("login.html", {"request": request})
    # fetch health + playlists
    rows = []
    for name, host in peers().items():
        try:
            h = requests.get(agent_url(host, "/api/health"), timeout=2).json()
            pl = requests.get(agent_url(host, "/api/playlist"), timeout=2).json()
        except Exception as e:
            h = {"ok": False, "name": name, "err": str(e)}
            pl = []
        rows.append({"name": name, "host": host, "health": h, "playlist": pl})
    return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "rows": rows})

@APP.post("/login")
def login(request: Request, password: str = Form(...)):
    if password == ENV["ADMIN_PASSWORD"]:
        request.session["auth"] = True
        return RedirectResponse("/", status_code=303)
    return RedirectResponse("/", status_code=303)

@APP.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

@APP.post("/api/kiosk/{name}/playlist")
def update_playlist(request: Request, name: str, body: dict):
    require_auth(request)
    p = peers()
    if name not in p: raise HTTPException(404, "Unknown kiosk")
    host = p[name]
    r = requests.post(agent_url(host, "/api/playlist"), json=body, headers=agent_headers(), timeout=5)
    return JSONResponse(r.json(), status_code=r.status_code)

@APP.post("/api/kiosk/{name}/reboot")
def reboot(request: Request, name: str):
    require_auth(request)
    p = peers()
    if name not in p: raise HTTPException(404, "Unknown kiosk")
    host = p[name]
    r = requests.post(agent_url(host, "/api/reboot"), headers=agent_headers(), timeout=3)
    return JSONResponse(r.json(), status_code=r.status_code)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:APP", host="0.0.0.0", port=int(ENV["ADMIN_PORT"]))
