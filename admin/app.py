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
-    env.setdefault("KIOSK_PEERS", "Infopoint1.local,InfoPoint2.local")
+    env.setdefault("KIOSK_PEERS", "Infopoint1.local,Infopoint2.local")
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
