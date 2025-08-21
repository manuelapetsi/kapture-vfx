## kapture-vfx

Invisible cloak for your webcam. Pick a color, make it vanish. Powered by OpenCV (CV), FastAPI (backend), and a zero-build modern UI.

### Features
- Real‑time color cloaking with background replacement
- Color picker + eyedropper from video
- Live tuning: tolerance, S/V floors, blur, morphology
- Mask preview, keep‑largest, min‑area, skin‑protect filters
- Toast notifications and responsive, sleek UI

### Requirements
- Python 3.9+
- macOS/Linux recommended
- A webcam and a visually distinct target color

### Quick start
```bash
cd /Users/scientific/i-apps/kapture-vfx
source venv/bin/activate
python3 -m pip install -r requirements.txt
./run.sh
```
Open `http://127.0.0.1:8000/`.

### How to use
1. Click Start and allow camera access.
2. Click Reset to capture a clean background (no target color in view).
3. Pick your target color (eyedropper or color input).
4. Tune Tolerance / S / V until the Preview mask highlights only the cloak.
5. Turn Preview off to enable the invisibility effect.

### Controls
- Color/Tolerance: primary selection and hue band width
- S min / V min: ignore dull/dark pixels
- Blur / Morph: stability and cleanup
- Keep largest / Min area / Skin protect: reduce false positives
- Preview mask: visualize detected pixels (green overlay)

### Tips
- Use even lighting and a matte, saturated cloak color.
- Re‑capture background after camera/scene changes.
- If frames “don’t align,” Reset after the camera settles.

### Health & endpoints
- UI: `/`
- WebSocket: `/ws`
- Health: `/health`

### License
MIT
