(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);

  const els = {
    home: $("#home"),
    listening: $("#listening"),
    verdict: $("#verdict"),
    setup: $("#setup"),
    modeChip: $("#modeChip"),
    setupBtn: $("#setupBtn"),

    startBtn: $("#startBtn"),
    stopBtn: $("#stopBtn"),
    againBtn: $("#againBtn"),
    sunaoBtn: $("#sunaoBtn"),
    lang: $("#lang"),
    inviteInput: $("#inviteInput"),
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
    verifyPanel: $("#verifyPanel"),
    verifyHint: $("#verifyHint"),
    trustedList: $("#trustedList"),
    call112: $("#call112"),
    safeWordBtn: $("#safeWordBtn"),
    safeWordMsg: $("#safeWordMsg"),
    guardianPanel: $("#guardianPanel"),
    guardianName: $("#guardianName"),
    guardianLink: $("#guardianLink"),
    gName: $("#gName"),
    gPhone: $("#gPhone"),
    contactRows: $("#contactRows"),
    addContactBtn: $("#addContactBtn"),
    saveSetupBtn: $("#saveSetupBtn"),
    voice: $("#voice"),
    landing: $("#landing"),
    scenarioBar: $("#scenarioBar"),
    verdictScenario: $("#verdictScenario"),
    brandBtn: $("#brandBtn"),
  };

  let ws = null;
  let audioCtx = null;
  let stream = null;
  let node = null;
  let currentLevel = "green";
  let APP_MODE = "mock";
  let currentScenario = null;

  const SCENARIOS = {
    scam: {
      fixture: "scam_demo_digital_arrest",
      title: "Digital-arrest call — scripted demo",
      expect: "Red: hang up.",
    },
    genuine: {
      fixture: "genuine_bank_otp_warning",
      title: "Genuine bank call — scripted demo",
      expect: "Green: no warning signs.",
    },
  };

  // ---- local settings ----
  function loadSettings() {
    try {
      return JSON.parse(localStorage.getItem("calleye.settings")) || {};
    } catch (e) {
      return {};
    }
  }
  function saveSettings(s) {
    localStorage.setItem("calleye.settings", JSON.stringify(s));
  }
  function getDeviceId() {
    let id = localStorage.getItem("calleye.device");
    if (!id) {
      id = "dev-" + Math.random().toString(36).slice(2, 10);
      localStorage.setItem("calleye.device", id);
    }
    return id;
  }

  function showScreen(name) {
    ["landing", "listening", "verdict", "setup"].forEach((s) => els[s].classList.add("hidden"));
    els[name].classList.remove("hidden");
  }

  async function fetchConfig() {
    try {
      const res = await fetch("/api/config");
      const cfg = await res.json();
      APP_MODE = cfg.mode || "mock";
      els.modeChip.textContent = cfg.live_mode ? "Live" : "Mock mode";
      return cfg;
    } catch (e) {
      els.modeChip.textContent = "offline";
      return null;
    }
  }

  // ---- voice clips (pre-generated at build time) ----
  let voiceManifest = null;
  async function loadVoiceManifest() {
    try {
      const res = await fetch("/audio/manifest.json");
      voiceManifest = await res.json();
    } catch (e) {
      voiceManifest = {};
    }
  }
  function playVoice(level) {
    const lang = els.lang.value || "hi";
    const key = lang + "/" + level;
    let src = voiceManifest && voiceManifest[key];
    if (!src) src = `/audio/${lang}/${level}.mp3`; // live-mode fallback
    els.voice.src = src;
    els.voice.play().catch(() => {});
  }

  // ---- setup UI ----
  function renderSetup() {
    const s = loadSettings();
    els.gName.value = s.guardian ? s.guardian.name : "";
    els.gPhone.value = s.guardian ? s.guardian.phone : "";
    els.inviteInput.value = localStorage.getItem("calleye.invite") || "";
    els.contactRows.innerHTML = "";
    (s.contacts || []).forEach((c) => addContactRow(c.name, c.phone));
    if (!s.contacts || s.contacts.length === 0) addContactRow("", "");
  }
  function addContactRow(name, phone) {
    const row = document.createElement("div");
    row.className = "contact-row";
    row.innerHTML =
      '<input type="text" placeholder="Name" class="c-name" value="' +
      escapeAttr(name) + '">' +
      '<input type="tel" placeholder="+91 phone" class="c-phone" value="' +
      escapeAttr(phone) + '">' +
      '<button class="btn">✕</button>';
    row.querySelector("button").addEventListener("click", () => row.remove());
    els.contactRows.appendChild(row);
  }
  function escapeAttr(v) {
    return String(v || "").replace(/"/g, "&quot;");
  }
  function saveSetup() {
    const contacts = [];
    els.contactRows.querySelectorAll(".contact-row").forEach((row) => {
      const name = row.querySelector(".c-name").value.trim();
      const phone = row.querySelector(".c-phone").value.trim();
      if (phone) contacts.push({ name: name || "Contact", phone });
    });
    const settings = {
      guardian: {
        name: els.gName.value.trim() || "Guardian",
        phone: els.gPhone.value.trim(),
      },
      contacts,
    };
    saveSettings(settings);
    localStorage.setItem("calleye.invite", els.inviteInput.value.trim());
    showScreen("landing");
  }

  // ---- transcript / analysis ----
  function appendTranscript(text, final) {
    const div = document.createElement("div");
    div.textContent = text;
    if (final) div.style.color = "var(--ink)";
    else div.style.color = "var(--muted)";
    els.transcript.appendChild(div);
    els.transcript.scrollTop = els.transcript.scrollHeight;
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
    currentLevel = a.level || "green";
    els.pressureFill.style.width = Math.min(100, a.pressure) + "%";
    els.pressureValue.textContent = Math.round(a.pressure);
    renderStages(a.stages || []);
    els.reasons.textContent = (a.reasons || []).join(" · ");
    els.verdictCard.className = "verdict-card " + currentLevel;

    if (a.level === "amber" || a.level === "red") {
      els.verdictLevel.textContent = a.level === "red" ? "🔴 Hang up" : "🟠 Careful";
      els.verdictText.textContent = a.screen_text;
      els.verdictReasons.textContent = (a.reasons || []).slice(0, 4).join(" · ");
    }
  }

  // ---- verify-first flow ----
  function showVerify(level) {
    const s = loadSettings();
    els.guardianPanel.classList.add("hidden");

    els.verifyPanel.classList.remove("hidden");
    els.trustedList.innerHTML = "";
    (s.contacts || []).forEach((c) => {
      const a = document.createElement("a");
      a.className = "btn";
      a.href = "tel:" + c.phone;
      a.textContent = "📞 Call " + c.name;
      els.trustedList.appendChild(a);
    });
    if ((!s.contacts || !s.contacts.length) && level === "red") {
      els.guardianPanel.classList.remove("hidden");
      els.guardianName.textContent = s.guardian ? s.guardian.name : "Guardian";
      els.guardianLink.href = guardianLink(s.guardian);
    }
    els.verifyHint.textContent =
      level === "red"
        ? "Hang up first. Then verify through a number you already have."
        : "Call back on a number you already have. Do not use a number the caller gives you.";
    els.safeWordMsg.textContent = "";
  }

  function guardianLink(guardian) {
    if (!guardian || !guardian.phone) return "#";
    const now = new Date();
    const msg = "CallEye alert: a suspicious call was flagged at " +
      now.toLocaleTimeString() + " on " + now.toLocaleDateString() +
      ". Please check on your loved one.";
    return "https://wa.me/" + guardian.phone.replace(/[^0-9]/g, "") +
      "?text=" + encodeURIComponent(msg);
  }

  function showVerdict(silent) {
    const s = loadSettings();
    const level = currentLevel;

    if (silent || level === "green") {
      showScreen("landing");
      return;
    }
    showScreen("verdict");

    if (level === "red") {
      els.guardianPanel.classList.remove("hidden");
      els.guardianName.textContent = s.guardian ? s.guardian.name : "Guardian";
      els.guardianLink.href = guardianLink(s.guardian);
      showVerify("red");
    } else {
      showVerify("amber");
    }
  }

  // ---- listening ----
  async function startListening(scenario) {
    await fetchConfig();
    showScreen("listening");
    els.transcript.innerHTML = "";
    els.reasons.textContent = "";
    els.pressureFill.style.width = "0%";
    els.pressureValue.textContent = "0";
    els.statusLine.textContent = "Starting…";
    currentLevel = "green";
    currentScenario = scenario || null;

    if (scenario) {
      els.scenarioBar.innerHTML =
        "<strong>" + scenario.title + "</strong>" +
        " &nbsp;·&nbsp; expected: " + scenario.expect;
      els.scenarioBar.style.display = "";
    } else if (APP_MODE === "mock") {
      els.scenarioBar.innerHTML =
        "<strong>Example call</strong> — scripted demo (digital-arrest pattern)";
      els.scenarioBar.style.display = "";
    } else {
      els.scenarioBar.style.display = "none";
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: true },
        video: false,
      });
    } catch (e) {
      if (APP_MODE !== "mock") {
        els.statusLine.textContent = "Microphone unavailable: " + e.message;
        return;
      }
      // Mock mode needs no mic: continue without audio capture.
      stream = null;
    }

    if (stream) {
      try {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        await audioCtx.audioWorklet.addModule("/audio-processor.js");
        node = new AudioWorkletNode(audioCtx, "downsampler-processor");
        const source = audioCtx.createMediaStreamSource(stream);
        source.connect(node);
      } catch (e) {
        // Audio capture is best-effort; mock mode still works without it.
        node = null;
      }
    }

    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = proto + "//" + location.host + "/ws/listen";
    ws = new WebSocket(wsUrl);

    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = () => reject(new Error("connection failed"));
    });

    const payload = {
      type: "start",
      lang: els.lang.value,
      code: localStorage.getItem("calleye.invite") || "",
      device_id: getDeviceId(),
    };
    // Mock mode: pick the replay fixture (scam vs genuine) for the demo.
    if (scenario && scenario.fixture) payload.fixture = scenario.fixture;
    else if (APP_MODE === "mock") payload.fixture = "scam_demo_digital_arrest";
    ws.send(JSON.stringify(payload));
    els.statusLine.textContent = "Listening… (on speaker)";

    if (node) {
      node.port.onmessage = (ev) => {
        if (ws && ws.readyState === WebSocket.OPEN) ws.send(ev.data);
      };
    }

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
      } else if (msg.type === "finished") {
        els.statusLine.textContent = "Call ended";
        finishDemo();
      }
    };

    ws.onclose = () => stopListening(true);
  }

  async function stopListening(silent) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "stop" }));
    if (ws) { try { ws.close(); } catch (e) {} ws = null; }
    if (node) { try { node.disconnect(); } catch (e) {} node = null; }
    if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
    if (audioCtx) { try { audioCtx.close(); } catch (e) {} audioCtx = null; }
    if (!silent) showVerdict(false);
  }

  function teardownCapture() {
    if (ws) { try { ws.close(); } catch (e) {} ws = null; }
    if (node) { try { node.disconnect(); } catch (e) {} node = null; }
    if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
    if (audioCtx) { try { audioCtx.close(); } catch (e) {} audioCtx = null; }
  }

  function showVerdictForce(level) {
    const lvl = level || "amber";
    els.verdictCard.className = "verdict-card " + lvl;
    els.verdictLevel.textContent =
      lvl === "red" ? "🔴 Hang up" : lvl === "amber" ? "🟠 Careful" : "🟢 No warning signs so far";
    els.verdictText.textContent =
      lvl === "red" ? "Hang up. Your guardian has been told."
      : lvl === "amber" ? "Careful. Check before you act."
      : "No warning signs so far. Check the caller calmly.";
    els.verdictReasons.textContent = els.reasons.textContent;
    els.verdictScenario.textContent = currentScenario
      ? currentScenario.title + " · expected: " + currentScenario.expect
      : (APP_MODE === "mock" ? "Example call — scripted demo" : "");
    showScreen("verdict");
  }

  function beginScenario(key) {
    const s = SCENARIOS[key];
    if (s) startListening(s);
  }

  function finishDemo() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try { ws.send(JSON.stringify({ type: "stop" })); } catch (e) {}
    }
    setTimeout(() => { teardownCapture(); showVerdictForce(currentLevel); }, 150);
  }

  // ---- events ----
  els.startBtn.addEventListener("click", () => startListening(null));
  els.stopBtn.addEventListener("click", () => stopListening(false));
  els.againBtn.addEventListener("click", () => showScreen("landing"));
  els.brandBtn.addEventListener("click", () => showScreen("landing"));
  document.querySelectorAll(".run-demo").forEach((btn) => {
    btn.addEventListener("click", () => {
      const card = btn.closest(".scenario-card");
      const key = card && card.getAttribute("data-scenario");
      if (key) beginScenario(key);
    });
  });
  els.sunaoBtn.addEventListener("click", () => playVoice(currentLevel || "green"));
  els.setupBtn.addEventListener("click", () => { renderSetup(); showScreen("setup"); });

  els.saveSetupBtn.addEventListener("click", saveSetup);
  els.addContactBtn.addEventListener("click", () => addContactRow("", ""));
  els.safeWordBtn.addEventListener("click", () => {
    els.safeWordMsg.textContent = "Ask for the family safe word you agreed on in person. A real emergency can survive two minutes of checking; a scam cannot.";
  });

  renderSetup();
  fetchConfig();
  loadVoiceManifest();
})();
