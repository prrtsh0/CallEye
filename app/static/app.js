(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);

  const els = {
    home: $("#home"),
    listening: $("#listening"),
    verdict: $("#verdict"),
    modeChip: $("#modeChip"),
    startBtn: $("#startBtn"),
    stopBtn: $("#stopBtn"),
    againBtn: $("#againBtn"),
    lang: $("#lang"),
    statusLine: $("#statusLine"),
    pressureFill: $("#pressureFill"),
    pressureValue: $("#pressureValue"),
    stageChips: $("#stageChips"),
    transcript: $("#transcript"),
    reasons: $("#reasons"),
    verdictCard: $("#verdictCard"),
    verdictLevel: $("#verdictLevel"),
    verdictText: $("#verdictText"),
    verdictReasons: $("#verdictReasons"),
  };

  let ws = null;
  let audioCtx = null;
  let stream = null;
  let node = null;

  function getDeviceId() {
    let id = localStorage.getItem("calleye.device");
    if (!id) {
      id = "dev-" + Math.random().toString(36).slice(2, 10);
      localStorage.setItem("calleye.device", id);
    }
    return id;
  }

  function showScreen(name) {
    ["home", "listening", "verdict"].forEach((s) => els[s].classList.add("hidden"));
    els[name].classList.remove("hidden");
  }

  async function fetchConfig() {
    try {
      const res = await fetch("/api/config");
      const cfg = await res.json();
      els.modeChip.textContent = cfg.live_mode ? "Live" : "Mock mode";
      return cfg;
    } catch (e) {
      els.modeChip.textContent = "offline";
      return null;
    }
  }

  function appendTranscript(text, final) {
    const div = document.createElement("div");
    div.textContent = text;
    if (final) div.style.color = "var(--ink)";
    else div.style.color = "var(--muted)";
    els.transcript.appendChild(div);
    els.transcript.scrollTop = els.transcript.scrollHeight;
  }

  function interfacePressure(level) {
    const colors = { green: "var(--green)", amber: "var(--amber)", red: "var(--red)" };
    els.pressureFill.style.background = colors[level] || "var(--green)";
    els.verdictCard.className = "verdict-card " + level;
  }

  function renderStages(stages) {
    const names = { authority: "Authority", fear: "Fear", isolation: "Isolation", urgency: "Urgency", ask: "Ask" };
    els.stageChips.innerHTML = "";
    Object.keys(names).forEach((k) => {
      const chip = document.createElement("span");
      chip.className = "chip" + (stages.indexOf(k) >= 0 ? " on" : "");
      chip.textContent = names[k];
      els.stageChips.appendChild(chip);
    });
  }

  function onAnalysis(a) {
    els.pressureFill.style.width = Math.min(100, a.pressure) + "%";
    els.pressureValue.textContent = Math.round(a.pressure);
    renderStages(a.stages || []);
    els.reasons.textContent = (a.reasons || []).join(" · ");
    interfacePressure(a.level);

    if (a.level === "amber" || a.level === "red") {
      els.verdictLevel.textContent = a.level === "red" ? "🔴 Hang up" : "🟠 Careful";
      els.verdictText.textContent = a.screen_text;
      els.verdictReasons.textContent = (a.reasons || []).slice(0, 4).join(" · ");
    }
  }

  async function startListening() {
    const cfg = await fetchConfig();
    showScreen("listening");
    els.transcript.innerHTML = "";
    els.reasons.textContent = "";
    els.pressureFill.style.width = "0%";
    els.pressureValue.textContent = "0";
    els.statusLine.textContent = "Starting…";

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: true,
        },
        video: false,
      });
    } catch (e) {
      els.statusLine.textContent = "Microphone unavailable: " + e.message;
      return;
    }

    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    await audioCtx.audioWorklet.addModule("/audio-processor.js");
    node = new AudioWorkletNode(audioCtx, "downsampler-processor");

    const source = audioCtx.createMediaStreamSource(stream);
    source.connect(node);

    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = proto + "//" + location.host + "/ws/listen";
    ws = new WebSocket(wsUrl);

    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = () => reject(new Error("connection failed"));
    });

    ws.send(JSON.stringify({
      type: "start",
      lang: els.lang.value,
      code: localStorage.getItem("calleye.invite") || "",
      device_id: getDeviceId(),
    }));
    els.statusLine.textContent = "Listening… (on speaker)";

    node.port.onmessage = (ev) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(ev.data); // binary PCM16 frame
      }
    };

    ws.onmessage = (ev) => {
      if (typeof ev.data !== "string") return;
      let msg;
      try { msg = JSON.parse(ev.data); } catch (e) { return; }
      if (msg.type === "transcript") appendTranscript(msg.text, msg.final);
      else if (msg.type === "analysis") onAnalysis(msg);
      else if (msg.type === "error") {
        els.statusLine.textContent = "Stopped (" + msg.code + ")";
        stopListening(true);
      } else if (msg.type === "budget") {
        els.statusLine.textContent = "Time left: " + msg.seconds_left + "s";
      }
    };

    ws.onclose = () => stopListening(true);
  }

  async function stopListening(silent) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "stop" }));
    }
    if (ws) { try { ws.close(); } catch (e) {} ws = null; }
    if (node) { try { node.disconnect(); } catch (e) {} node = null; }
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      stream = null;
    }
    if (audioCtx) { try { audioCtx.close(); } catch (e) {} audioCtx = null; }

    const level = els.verdictCard.className.split(" ").pop();
    if (!silent && (level === "amber" || level === "red")) {
      showScreen("verdict");
    } else if (!silent) {
      showScreen("home");
    }
  }

  els.startBtn.addEventListener("click", startListening);
  els.stopBtn.addEventListener("click", () => stopListening(false));
  els.againBtn.addEventListener("click", () => showScreen("home"));

  fetchConfig();
})();
