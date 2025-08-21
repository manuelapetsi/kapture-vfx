# kapture-vfx

A Harry Potter-style invisible cloak app using FastAPI (backend), OpenCV (CV), and a sleek, modern frontend (Tailwind, Vue via CDN, Font Awesome, Hammer.js). No auth required.

## Requirements

- Python 3.9+
- macOS/Linux recommended
- Webcam access via browser

## Setup

```bash
cd /Users/scientific/i-apps/kapture-vfx
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Run

```bash
./run.sh
# or
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/` in your browser.

## Usage

- Allow webcam access when the page loads
- Click Start to begin streaming; processed frames show on the right
- Click Reset Background (or double tap anywhere) to recapture a clean background
- Use the color picker and tolerance slider (top-right) to choose the target color live
- Wear or show the chosen color; those pixels become invisible and are replaced with the captured background

## Tune Target Color

The CV effect uses HSV thresholds derived from your chosen color. For programmatic defaults, edit `app/services/processor.py` constructor or call the WebSocket with `{ type: 'set_color', hex: '#RRGGBB', tolerance: 10 }`.

## Notes

- Frontend uses CDN builds for zero-build setup (Tailwind, Vue 3, Font Awesome, Hammer.js)
- WebSocket endpoint: `/ws` expects JSON `{ type: 'frame', data: 'data:image/jpeg;base64,...' }`
- Health check: `GET /health` returns `{ status: 'ok' }`
