const FRAME_INTERVAL_MS = 1000 / 15;
const LONG_PRESS_MS = 320;

const friendlyMessages = {
  bad_frame: "The incoming camera frame could not be decoded.",
  camera_not_supported: "This browser does not expose camera access.",
  camera_start_failed: "The camera could not be started.",
  frame_too_large: "The current camera frame is too large for the server limit.",
  internal_error: "The server hit an unexpected error while processing the frame.",
  invalid_frame_data: "The frame payload was missing or malformed.",
  invalid_hex_color: "The selected color was not valid.",
  invalid_json: "The browser sent malformed JSON to the WebSocket.",
  invalid_message: "The browser sent a message the server could not understand.",
  message_too_large: "The message exceeded the configured WebSocket size limit.",
  rate_limit_exceeded: "Frame rate limit reached. The stream will keep retrying at a lower pace.",
  socket_connect_failed: "The browser could not establish the WebSocket connection.",
  unknown_message_type: "The server rejected an unknown message type.",
};

document.addEventListener("DOMContentLoaded", () => {
  const elements = {
    video: document.getElementById("cameraVideo"),
    processedImage: document.getElementById("processedImage"),
    emptyState: document.getElementById("emptyState"),
    emptyTitle: document.querySelector(".empty-title"),
    emptyDesc: document.querySelector(".empty-desc"),
    toggleStreamButton: document.getElementById("toggleStreamButton"),
    resetButton: document.getElementById("resetButton"),
    pickButton: document.getElementById("pickButton"),
    helpButton: document.getElementById("helpButton"),
    helpModal: document.getElementById("helpModal"),
    closeHelpButton: document.getElementById("closeHelpButton"),
    connStatus: document.getElementById("connStatus"),
    connDot: document.getElementById("connDot"),
    fpsValue: document.getElementById("fpsValue"),
    sessionTimer: document.getElementById("sessionTimer"),
    pickHint: document.getElementById("pickHint"),
    hex: document.getElementById("hex"),
    hexValue: document.getElementById("hexValue"),
    tolerance: document.getElementById("tolerance"),
    toleranceValue: document.getElementById("toleranceValue"),
    sMin: document.getElementById("sMin"),
    sMinValue: document.getElementById("sMinValue"),
    vMin: document.getElementById("vMin"),
    vMinValue: document.getElementById("vMinValue"),
    blur: document.getElementById("blur"),
    blurValue: document.getElementById("blurValue"),
    morphIter: document.getElementById("morphIter"),
    morphIterValue: document.getElementById("morphIterValue"),
    minAreaPct: document.getElementById("minAreaPct"),
    minAreaPctValue: document.getElementById("minAreaPctValue"),
    previewMask: document.getElementById("previewMask"),
    keepLargest: document.getElementById("keepLargest"),
    skinProtect: document.getElementById("skinProtect"),
    toastStack: document.getElementById("toastStack"),
  };

  const pipelineSteps = document.querySelectorAll(".pipe-step");

  const state = {
    ws: null,
    stream: null,
    streaming: false,
    connected: false,
    hasColor: false,
    awaitingFrame: false,
    picking: false,
    animationId: null,
    lastSentAt: 0,
    lastFrameAt: 0,
    manualDisconnect: false,
    longPressTimerId: 0,
    toastTimerId: 0,
    recentToast: new Map(),
    sessionStartTime: 0,
    sessionTimerInterval: 0,
  };

  const frameCanvas = document.createElement("canvas");
  const frameContext = frameCanvas.getContext("2d", { alpha: false });

  function pushToast(message, key = "", ttlMs = 2200, variant = "info") {
    const now = Date.now();
    if (key) {
      const lastSeen = state.recentToast.get(key);
      if (lastSeen && now - lastSeen < ttlMs) {
        return;
      }
      state.recentToast.set(key, now);
    }

    window.clearTimeout(state.toastTimerId);
    elements.toastStack.replaceChildren();

    const toast = document.createElement("article");
    toast.className = `toast ${variant}`;

    const title = document.createElement("p");
    title.className = "toast-title";
    title.textContent = variant === "error" ? "Issue" : "Status";

    const body = document.createElement("p");
    body.className = "toast-message";
    body.textContent = message;

    toast.append(title, body);
    elements.toastStack.appendChild(toast);

    state.toastTimerId = window.setTimeout(() => {
      if (toast.isConnected) {
        toast.remove();
      }
    }, ttlMs);
  }

  function setConnectionStatus(connected) {
    state.connected = connected;
    elements.connStatus.dataset.status = connected ? "ok" : "off";
    elements.connStatus.textContent = connected ? "Live" : "Offline";
    if (elements.connDot) {
      elements.connDot.classList.toggle("is-live", connected);
    }
  }

  function startSessionTimer() {
    state.sessionStartTime = Date.now();
    stopSessionTimer();
    state.sessionTimerInterval = window.setInterval(() => {
      const elapsed = Math.floor((Date.now() - state.sessionStartTime) / 1000);
      const min = String(Math.floor(elapsed / 60)).padStart(2, "0");
      const sec = String(elapsed % 60).padStart(2, "0");
      if (elements.sessionTimer) {
        elements.sessionTimer.textContent = `${min}:${sec}`;
      }
    }, 1000);
  }

  function stopSessionTimer() {
    if (state.sessionTimerInterval) {
      window.clearInterval(state.sessionTimerInterval);
      state.sessionTimerInterval = 0;
    }
    if (elements.sessionTimer) {
      elements.sessionTimer.textContent = "00:00";
    }
  }

  function updatePipeline() {
    pipelineSteps.forEach((step) => {
      step.classList.remove("is-active", "is-done");
    });

    if (state.streaming) {
      if (pipelineSteps[0]) pipelineSteps[0].classList.add("is-active");
    }
    if (state.picking && pipelineSteps[1]) {
      pipelineSteps[1].classList.add("is-active");
    }
    if (state.hasColor) {
      if (pipelineSteps[0]) pipelineSteps[0].classList.add("is-done");
      if (pipelineSteps[1]) pipelineSteps[1].classList.add("is-done");
      if (state.streaming && pipelineSteps[2]) {
        pipelineSteps[2].classList.add("is-active");
      }
    }
  }

  function setStreamingState(streaming) {
    state.streaming = streaming;
    elements.toggleStreamButton.dataset.state = streaming ? "active" : "idle";
    elements.toggleStreamButton.textContent = "";

    const dot = document.createElement("span");
    dot.className = "btn-dot";
    elements.toggleStreamButton.appendChild(dot);
    elements.toggleStreamButton.append(streaming ? " Stop Session" : " Start Session");

    if (streaming) {
      startSessionTimer();
    } else {
      stopSessionTimer();
    }
    updatePipeline();
  }

  function setPickingState(picking) {
    state.picking = picking;
    elements.video.classList.toggle("is-picking", picking);
    elements.pickHint.hidden = !picking;
    updatePipeline();
  }

  function syncValueDisplays() {
    elements.hexValue.textContent = elements.hex.value.toUpperCase();
    elements.toleranceValue.textContent = elements.tolerance.value;
    elements.sMinValue.textContent = elements.sMin.value;
    elements.vMinValue.textContent = elements.vMin.value;
    elements.blurValue.textContent = elements.blur.value;
    elements.morphIterValue.textContent = elements.morphIter.value;
    elements.minAreaPctValue.textContent = `${elements.minAreaPct.value}%`;
  }

  function syncProcessedState() {
    const hasImage = Boolean(elements.processedImage.getAttribute("src"));
    if (state.hasColor && hasImage) {
      elements.processedImage.hidden = false;
      elements.emptyState.hidden = true;
      return;
    }

    elements.processedImage.hidden = true;
    elements.emptyState.hidden = false;

    if (elements.emptyTitle) {
      elements.emptyTitle.textContent = state.hasColor
        ? "Processing..."
        : "No output yet";
    }
    if (elements.emptyDesc) {
      elements.emptyDesc.textContent = state.hasColor
        ? "Waiting for processed frames"
        : "Select a target color to begin processing";
    }
  }

  function setProcessedSource(dataUri) {
    elements.processedImage.setAttribute("src", dataUri);
    syncProcessedState();
  }

  function clearAnimationLoop() {
    if (state.animationId !== null) {
      window.cancelAnimationFrame(state.animationId);
      state.animationId = null;
    }
  }

  function clearLongPressTimer() {
    if (state.longPressTimerId) {
      window.clearTimeout(state.longPressTimerId);
      state.longPressTimerId = 0;
    }
  }

  function ensureFrameCanvasSize() {
    const width = elements.video.videoWidth;
    const height = elements.video.videoHeight;
    if (!width || !height) {
      return false;
    }

    if (frameCanvas.width !== width || frameCanvas.height !== height) {
      frameCanvas.width = width;
      frameCanvas.height = height;
    }
    return true;
  }

  function drawCurrentVideoFrame() {
    if (!ensureFrameCanvasSize()) {
      return false;
    }
    frameContext.drawImage(elements.video, 0, 0, frameCanvas.width, frameCanvas.height);
    return true;
  }

  function sendSocketMessage(payload) {
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
      return false;
    }
    state.ws.send(JSON.stringify(payload));
    return true;
  }

  function updateFps() {
    const now = performance.now();
    if (state.lastFrameAt > 0) {
      const delta = now - state.lastFrameAt;
      if (delta > 0) {
        elements.fpsValue.textContent = String(Math.round(1000 / delta));
      }
    }
    state.lastFrameAt = now;
  }

  function formatMessage(code) {
    return friendlyMessages[code] || code.replaceAll("_", " ");
  }

  function disconnectSocket() {
    if (!state.ws) {
      return;
    }

    const socket = state.ws;
    state.ws = null;
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      socket.close(1000, "client_stop");
    }
  }

  function stopStreaming(showToast = true) {
    clearAnimationLoop();
    state.awaitingFrame = false;
    state.lastSentAt = 0;
    state.lastFrameAt = 0;
    if (!state.streaming && !state.ws) {
      return;
    }

    setStreamingState(false);
    state.manualDisconnect = true;
    disconnectSocket();
    cleanupCamera();
    if (showToast) {
      pushToast("Streaming stopped.", "stream-stop");
    }
  }

  function cleanupCamera() {
    if (!state.stream) {
      return;
    }
    for (const track of state.stream.getTracks()) {
      track.stop();
    }
    state.stream = null;
    elements.video.srcObject = null;
  }

  async function ensureCamera() {
    if (state.stream) {
      return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("camera_not_supported");
    }

    state.stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    elements.video.srcObject = state.stream;
    try {
      await elements.video.play();
    } catch (error) {
      throw new Error("camera_start_failed");
    }
  }

  function handleSocketMessage(event) {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (error) {
      pushToast("Received a malformed response from the server.", "bad-server-json", 2600, "error");
      return;
    }

    if (!message || typeof message !== "object") {
      return;
    }

    if (message.type === "frame" && typeof message.data === "string") {
      state.awaitingFrame = false;
      updateFps();
      setProcessedSource(message.data);
      return;
    }

    if (message.type === "toast" && typeof message.message === "string") {
      pushToast(message.message, `toast-${message.message}`);
      return;
    }

    if (message.type === "error" && typeof message.message === "string") {
      state.awaitingFrame = false;
      pushToast(formatMessage(message.message), `error-${message.message}`, 2600, "error");
    }
  }

  function connectWebSocket() {
    if (state.ws && (state.ws.readyState === WebSocket.OPEN || state.ws.readyState === WebSocket.CONNECTING)) {
      return Promise.resolve();
    }

    state.manualDisconnect = false;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws`);
    state.ws = socket;

    return new Promise((resolve, reject) => {
      let settled = false;

      socket.addEventListener("open", () => {
        setConnectionStatus(true);
        applyColor();
        sendParams();
        settled = true;
        resolve();
      });

      socket.addEventListener("message", handleSocketMessage);

      socket.addEventListener("close", () => {
        const wasManual = state.manualDisconnect;
        state.manualDisconnect = false;
        state.awaitingFrame = false;
        if (state.ws === socket) {
          state.ws = null;
        }
        setConnectionStatus(false);

        if (state.streaming && !wasManual) {
          clearAnimationLoop();
          setStreamingState(false);
          pushToast("Connection closed unexpectedly.", "socket-closed", 2600, "error");
        }

        if (!settled) {
          settled = true;
          reject(new Error("socket_connect_failed"));
        }
      });

      socket.addEventListener("error", () => {
        if (!settled) {
          settled = true;
          reject(new Error("socket_connect_failed"));
        }
      });
    });
  }

  function applyColor() {
    const hex = elements.hex.value.trim();
    if (!/^#[0-9a-fA-F]{6}$/.test(hex)) {
      pushToast("Pick a valid six-digit hex color.", "invalid-color", 2200, "error");
      return;
    }

    state.hasColor = true;
    syncProcessedState();
    updatePipeline();
    sendSocketMessage({
      type: "set_color",
      hex,
      tolerance: Number(elements.tolerance.value),
      s_min: Number(elements.sMin.value),
      v_min: Number(elements.vMin.value),
    });
  }

  function sendParams() {
    sendSocketMessage({
      type: "set_params",
      blur_ksize: Number(elements.blur.value),
      morph_iterations: Number(elements.morphIter.value),
      preview_mask: elements.previewMask.checked,
      keep_largest: elements.keepLargest.checked,
      skin_protect: elements.skinProtect.checked,
      min_area_ratio: Number(elements.minAreaPct.value) / 100,
    });
  }

  function resetBackground() {
    if (!sendSocketMessage({ type: "reset_background" })) {
      pushToast("Start the stream before resetting the background.", "reset-before-stream", 2200, "error");
    }
  }

  function captureLoop(timestamp) {
    if (!state.streaming) {
      return;
    }

    if (
      state.ws &&
      state.ws.readyState === WebSocket.OPEN &&
      state.ws.bufferedAmount === 0 &&
      !state.awaitingFrame &&
      timestamp - state.lastSentAt >= FRAME_INTERVAL_MS &&
      drawCurrentVideoFrame()
    ) {
      const data = frameCanvas.toDataURL("image/jpeg", 0.6);
      state.awaitingFrame = true;
      state.lastSentAt = timestamp;
      state.ws.send(JSON.stringify({ type: "frame", data }));
    }

    state.animationId = window.requestAnimationFrame(captureLoop);
  }

  async function toggleStreaming() {
    if (state.streaming) {
      stopStreaming();
      return;
    }

    try {
      await ensureCamera();
      await connectWebSocket();
      state.awaitingFrame = false;
      state.lastSentAt = 0;
      state.lastFrameAt = 0;
      setStreamingState(true);
      clearAnimationLoop();
      state.animationId = window.requestAnimationFrame(captureLoop);
      pushToast("Streaming started.", "stream-start");
    } catch (error) {
      state.manualDisconnect = false;
      disconnectSocket();
      setConnectionStatus(false);
      pushToast(formatMessage(error.message || "socket_connect_failed"), "stream-start-failed", 2600, "error");
    }
  }

  function rgbToHex(r, g, b) {
    return `#${[r, g, b].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
  }

  function sampleColorAt(clientX, clientY, size = 11) {
    if (!drawCurrentVideoFrame()) {
      return null;
    }

    const rect = elements.video.getBoundingClientRect();
    const x = Math.round(((clientX - rect.left) * frameCanvas.width) / rect.width);
    const y = Math.round(((clientY - rect.top) * frameCanvas.height) / rect.height);
    const half = Math.max(1, Math.floor(size / 2));
    const sx = Math.max(0, x - half);
    const sy = Math.max(0, y - half);
    const sw = Math.min(frameCanvas.width - sx, half * 2 + 1);
    const sh = Math.min(frameCanvas.height - sy, half * 2 + 1);
    const imageData = frameContext.getImageData(sx, sy, sw, sh);

    let rSum = 0;
    let gSum = 0;
    let bSum = 0;
    let count = 0;

    for (let index = 0; index < imageData.data.length; index += 4) {
      rSum += imageData.data[index];
      gSum += imageData.data[index + 1];
      bSum += imageData.data[index + 2];
      count += 1;
    }

    if (!count) {
      return null;
    }

    return rgbToHex(
      Math.round(rSum / count),
      Math.round(gSum / count),
      Math.round(bSum / count),
    );
  }

  function pickColorAt(clientX, clientY) {
    const color = sampleColorAt(clientX, clientY, 11);
    if (!color) {
      pushToast("No video frame is available to sample yet.", "pick-no-frame", 2200, "error");
      return;
    }

    elements.hex.value = color;
    applyColor();
    setPickingState(false);
    pushToast("Target color sampled.", "pick-color");
  }

  function openHelp() {
    elements.helpModal.hidden = false;
    document.body.classList.add("modal-open");
  }

  function closeHelp() {
    elements.helpModal.hidden = true;
    document.body.classList.remove("modal-open");
  }

  function scheduleLongPress(event) {
    clearLongPressTimer();
    const { clientX, clientY } = event;
    state.longPressTimerId = window.setTimeout(() => {
      pickColorAt(clientX, clientY);
      state.longPressTimerId = 0;
    }, LONG_PRESS_MS);
  }

  function teardown() {
    stopStreaming(false);
    clearLongPressTimer();
    cleanupCamera();
    stopSessionTimer();
  }

  elements.toggleStreamButton.addEventListener("click", toggleStreaming);
  elements.resetButton.addEventListener("click", resetBackground);
  elements.pickButton.addEventListener("click", async () => {
    try {
      await ensureCamera();
      setPickingState(true);
      pushToast("Click or long press the camera frame to sample a color.", "pick-mode");
    } catch (error) {
      pushToast(formatMessage(error.message || "camera_start_failed"), "pick-camera", 2600, "error");
    }
  });
  elements.helpButton.addEventListener("click", openHelp);
  elements.closeHelpButton.addEventListener("click", closeHelp);
  elements.helpModal.addEventListener("click", (event) => {
    if (event.target === elements.helpModal) {
      closeHelp();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setPickingState(false);
      closeHelp();
    }
  });

  elements.video.addEventListener("click", (event) => {
    if (!state.picking) {
      return;
    }
    pickColorAt(event.clientX, event.clientY);
  });
  elements.video.addEventListener("pointerdown", scheduleLongPress);
  elements.video.addEventListener("pointermove", clearLongPressTimer);
  elements.video.addEventListener("pointerup", clearLongPressTimer);
  elements.video.addEventListener("pointercancel", clearLongPressTimer);
  elements.video.addEventListener("pointerleave", clearLongPressTimer);

  elements.hex.addEventListener("change", applyColor);
  elements.tolerance.addEventListener("input", () => {
    syncValueDisplays();
    applyColor();
  });
  elements.sMin.addEventListener("input", () => {
    syncValueDisplays();
    applyColor();
  });
  elements.vMin.addEventListener("input", () => {
    syncValueDisplays();
    applyColor();
  });
  elements.blur.addEventListener("input", () => {
    syncValueDisplays();
    sendParams();
  });
  elements.morphIter.addEventListener("input", () => {
    syncValueDisplays();
    sendParams();
  });
  elements.minAreaPct.addEventListener("input", () => {
    syncValueDisplays();
    sendParams();
  });
  elements.previewMask.addEventListener("change", sendParams);
  elements.keepLargest.addEventListener("change", sendParams);
  elements.skinProtect.addEventListener("change", sendParams);

  window.addEventListener("beforeunload", teardown);

  syncValueDisplays();
  syncProcessedState();
  setConnectionStatus(false);
  setStreamingState(false);
  setPickingState(false);
});
