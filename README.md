## kapture-vfx

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.x-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8.svg?logo=opencv&logoColor=white)](https://opencv.org/)
[![Realtime](https://img.shields.io/badge/Realtime-WebSocket-1E90FF.svg)](#)
[![UI](https://img.shields.io/badge/UI-Tailwind%20CSS%20%2B%20Vue-38B2AC.svg?logo=tailwind-css&logoColor=white)](#)
[![GitHub stars](https://img.shields.io/github/stars/manuelapetsi/kapture-vfx?style=social)](https://github.com/manuelapetsi/kapture-vfx)

Invisible cloak for your webcam. Pick a color, make it vanish. Powered by OpenCV (CV), FastAPI (backend), and a zero-build modern UI.

### Project structure
```text
kapture-vfx/
├─ app/
│  ├─ __init__.py
│  ├─ main.py                 # FastAPI entry (routes + static)
│  ├─ ws.py                   # WebSocket frame handling
│  ├─ cv/
│  │  ├─ __init__.py
│  │  └─ invisibility.py      # Mask building + cloaking
│  └─ services/
│     ├─ __init__.py
│     └─ processor.py         # Base64 encode/decode, color + params
├─ public/
│  └─ index.html              # Tailwind + Vue UI (CDN)
├─ run.sh                     # Dev server launcher
├─ requirements.txt
├─ README.md
└─ LICENSE
```

### Tech stack
- Backend [![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/) [![Starlette](https://img.shields.io/badge/Starlette-0A0A0A.svg)](https://www.starlette.io/)
- Computer Vision [![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8.svg?logo=opencv&logoColor=white)](https://opencv.org/) [![NumPy](https://img.shields.io/badge/NumPy-013243.svg?logo=numpy&logoColor=white)](https://numpy.org/)
- Frontend [![Tailwind CSS](https://img.shields.io/badge/Tailwind-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/) [![Vue 3](https://img.shields.io/badge/Vue%203-42B883.svg?logo=vue.js&logoColor=white)](https://vuejs.org/) [![Font Awesome](https://img.shields.io/badge/Font%20Awesome-528DD7.svg?logo=fontawesome&logoColor=white)](https://fontawesome.com/) [![Hammer.js](https://img.shields.io/badge/Hammer.js-FF9800.svg)](https://hammerjs.github.io/)
- Realtime [![WebSocket](https://img.shields.io/badge/WebSocket-1E90FF.svg)](#) [![Uvicorn](https://img.shields.io/badge/Uvicorn-121212.svg)](https://www.uvicorn.org/)

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
