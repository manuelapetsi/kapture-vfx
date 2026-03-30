from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .security import SECURE_RESPONSE_HEADERS, get_allowed_hosts
from .ws import handle_ws

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"

app = FastAPI(title="kapture-vfx")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=get_allowed_hosts())


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    for name, value in SECURE_RESPONSE_HEADERS.items():
        response.headers.setdefault(name, value)
    return response

app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(PUBLIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": "kapture-vfx"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handle_ws(websocket)
