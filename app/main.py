from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from .ws import handle_ws

app = FastAPI(title="kapture-vfx")

app.add_middleware(CORSMiddleware,
	allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
	allow_credentials=False,
	allow_methods=["GET", "POST"],
	allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="public"), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
	return FileResponse("public/index.html")

@app.get("/health")
def health():
	return {"status": "ok", "service": "kapture-vfx"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
	await handle_ws(websocket)
