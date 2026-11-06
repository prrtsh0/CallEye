// CallEye app (PWA). Hash-routed. Practice mode by default; live needs a code.
import { createDemoEngine, createResultView } from "/shared/result-view.js";
import { MODE_BADGE } from "/shared/i18n-core.js";

const $ = (s) => document.querySelector(s);

const els = {
  welcome: $("#view-welcome"),
  setup: $("#view-setup"),
  home: $("#view-home"),
  practice: $("#view-practice"),
  live: $("#view-live"),
  upload: $("#view-upload"),
  modeBadge: $("#modeBadge"),
  settingsHint: $("#settingsHint"),
  welcomeStart: $("#welcomeStart"),
  setupSave: $("#setupSave"),
  practiceBtn: $("#practiceBtn"),
  liveBtn: $("#liveBtn"),
  uploadBtn: $("#uploadBtn"),
  backHome: $("#backHome"),
  backLiveHome: $("#backLiveHome"),
  backUploadHome: $("#backUploadHome"),
  brandHome: $("#brandHome"),
  practiceResult: $("#practiceResult"),
  liveStatus: $("#liveStatus"),
  liveResult: $("#liveResult"),
  unlockSheet: $("#unlockSheet"),
  unlockInput: $("#unlockInput"),
  unlockMsg: $("#unlockMsg"),
  unlockSubmit: $("#unlockSubmit"),
  unlockCancel: $("#unlockCancel"),
  forgetBtn: $("#forgetBtn"),
  gName: $("#gName"),
  gPhone: $("#gPhone"),
  uploadFile: $("#uploadFile"),
  uploadGo: $("#uploadGo"),
  uploadOut: $("#uploadOut"),
};

const routes = {
  welcome: "view-welcome",
  setup: "view-setup",
  home: "view-home",
  practice: "view-practice",
  live: "view-live",
  upload: "view-upload",
};

const state = {
  setupDone: !!localStorage.getItem("calleye.setup"),
  accessCode: localStorage.getItem("calleye.access_code") || "",
  liveEnabled: false,
  dailyCap: 0,
  lang: "en",
};

function show(name) {
  Object.values(routes).forEach((id) => $("#" + id).classList.add("hidden"));
  $("#" + routes[name]).classList.remove("hidden");
  if (location.hash !== "#/" + name) history.replaceState(null, "", "#/" + name);
}

function getDeviceId() {
  let id = localStorage.getItem("calleye.device");
  if (!id) {
    id = "dev-" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem("calleye.device", id);
  }
  return id;
}

function updateBadge() {
  if (state.liveEnabled && state.accessCode) {
    els.modeBadge.textContent = MODE_BADGE.live;
    els.modeBadge.classList.add("live");
  } else {
    els.modeBadge.textContent = MODE_BADGE.practice;
    els.modeBadge.classList.remove("live");
  }
}

function fetchConfig() {
  return fetch("/api/config")
    .then((r) => r.json())
    .then((cfg) => {
      state.liveEnabled = !!(cfg.live_mode && cfg.invite_required);
      state.dailyCap = cfg.daily_cap_per_device || 0;
      updateBadge();
    })
    .catch(() => {});
}

// free-tier cold start: if /healthz is slower than 2s, say so.
function checkWake() {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 2000);
  return fetch("/healthz", { signal: ctrl.signal })
    .then(() => true)
    .catch(() => false)
    .finally(() => clearTimeout(t));
}

// ---- practice call (runs the REAL backend detector; no mic, no credits) ----
const practiceView = createResultView(els.practiceResult);
let practiceTimers = [];
let practiceCancelled = false;

function stopPractice() {
  practiceCancelled = true;
  practiceTimers.forEach(clearTimeout);
  practiceTimers = [];
}

function playPractice() {
  stopPractice();
  practiceCancelled = false;
  practiceView.reset();
  practiceView.setScenario("Digital-arrest sample (real detector)");

  fetch("/api/practice/demo_digital_arrest", { method: "POST" })
    .then((r) => {
      if (!r.ok) throw new Error("practice endpoint failed");
      return r.json();
    })
    .then((data) => {
      const events = data.events || [];
      const speed = 1.4;
      events.forEach((ev, i) => {
        const delay = (ev.t * 1000) / speed;
        practiceTimers.push(setTimeout(() => {
          if (practiceCancelled) return;
          if (ev.type === "transcript") {
            practiceView.appendCaption(ev.text, true);
          } else if (ev.type === "analysis") {
            practiceView.setStages(ev.stages || []);
            practiceView.setPressure(ev.pressure);
            practiceView.setLevel(ev.level);
            practiceView.showVerify(ev.level === "amber" || ev.level === "red");
          }
        }, delay));
      });
    })
    .catch(() => {
      practiceView.setStatus("Could not reach the detector.");
    });
}

// ---- live unlock ----
function openUnlock() {
  els.unlockMsg.textContent = "";
  els.unlockMsg.className = "msg";
  els.unlockInput.value = "";
  els.unlockSheet.classList.remove("hidden");
  els.unlockInput.focus();
}
function closeUnlock() {
  els.unlockSheet.classList.add("hidden");
}

async function submitUnlock() {
  const code = els.unlockInput.value.trim();
  if (!code) {
    els.unlockMsg.textContent = "Enter a code.";
    els.unlockMsg.className = "msg err";
    return;
  }
  try {
    const r = await fetch("/api/unlock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    if (r.status === 429) {
      els.unlockMsg.textContent = "Too many attempts. Try again later.";
      els.unlockMsg.className = "msg err";
      return;
    }
    if (!r.ok) {
      els.unlockMsg.textContent = "Incorrect code.";
      els.unlockMsg.className = "msg err";
      return;
    }
    const data = await r.json();
    localStorage.setItem("calleye.access_code", code);
    state.accessCode = code;
    state.dailyCap = data.daily_allowance || state.dailyCap;
    closeUnlock();
    updateBadge();
    startLive();
  } catch (e) {
    els.unlockMsg.textContent = "Network error. Try again.";
    els.unlockMsg.className = "msg err";
  }
}

// ---- live session (server validates the code on every start) ----
const liveEngine = createDemoEngine(els.liveResult);
const liveView = liveEngine.view;

function startLive() {
  show("live");
  els.liveStatus.textContent = "Connecting…";
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(proto + "//" + location.host + "/ws/listen");

  ws.onopen = () => {
    ws.send(JSON.stringify({
      type: "start",
      lang: state.lang,
      device_id: getDeviceId(),
      code: state.accessCode,
      fixture: "demo_digital_arrest",
    }));
    els.liveStatus.textContent = "Listening…";
  };
  ws.onerror = () => { els.liveStatus.textContent = "Connection failed."; };
  ws.onmessage = (ev) => {
    if (typeof ev.data !== "string") return;
    let m;
    try { m = JSON.parse(ev.data); } catch (e) { return; }
    if (m.type === "transcript") {
      liveView.appendCaption(m.text, m.final);
    } else if (m.type === "analysis") {
      const active = Object.keys(m.stages || {}).filter((k) => m.stages[k]);
      liveView.setStages(active);
      liveView.setPressure(m.pressure);
      liveView.setLevel(m.level);
      liveView.showVerify(m.level === "amber" || m.level === "red");
    } else if (m.type === "error") {
      els.liveStatus.textContent = "Stopped (" + m.code + ")";
      ws.close();
    }
  };
}

// ---- upload (works without a code) ----
async function runUpload() {
  const f = els.uploadFile.files[0];
  if (!f) { els.uploadOut.textContent = "Choose an audio file first."; return; }
  els.uploadOut.textContent = "Analysing…";
  const fd = new FormData();
  fd.append("file", f);
  fd.append("lang", state.lang);
  try {
    const r = await fetch("/api/transcribe", { method: "POST", body: fd });
    const j = await r.json();
    els.uploadOut.innerHTML =
      "<strong>Level:</strong> " + (j.level || "?") +
      " &nbsp; <strong>Pressure:</strong> " + (j.pressure || 0) +
      (j.transcript ? "<br><strong>Transcript:</strong> " + j.transcript : "");
  } catch (e) {
    els.uploadOut.textContent = "Could not analyse that file.";
  }
}

// ---- events ----
els.welcomeStart.addEventListener("click", () => show("setup"));
els.setupSave.addEventListener("click", () => {
  localStorage.setItem("calleye.setup", "1");
  state.setupDone = true;
  show("home");
});
els.practiceBtn.addEventListener("click", () => { show("practice"); playPractice(); });
els.liveBtn.addEventListener("click", () => {
  if (!state.liveEnabled) {
    els.settingsHint.textContent = "Live mode is off right now.";
    return;
  }
  if (!state.accessCode) openUnlock();
  else startLive();
});
els.uploadBtn.addEventListener("click", () => show("upload"));
els.backHome.addEventListener("click", () => { stopPractice(); show("home"); });
els.backLiveHome.addEventListener("click", () => show("home"));
els.backUploadHome.addEventListener("click", () => show("home"));
els.brandHome.addEventListener("click", () => show("home"));
els.unlockSubmit.addEventListener("click", submitUnlock);
els.unlockCancel.addEventListener("click", closeUnlock);
els.forgetBtn.addEventListener("click", () => {
  localStorage.removeItem("calleye.access_code");
  state.accessCode = "";
  updateBadge();
  els.settingsHint.textContent = "Access code forgotten. You are signed out of live mode.";
});
els.uploadGo.addEventListener("click", runUpload);

// Register the service worker ONLY from the app (scope /app/). The landing
// never registers a service worker.
if ("serviceWorker" in navigator && location.pathname.startsWith("/app")) {
  navigator.serviceWorker.register("/app/sw.js", { scope: "/app/" }).catch(() => {});
}

// ---- boot ----
function boot() {
  const wasFast = checkWake();
  if (!wasFast) {
    els.modeBadge.textContent = "Waking up the app, one moment";
    setTimeout(() => { if (!(state.liveEnabled && state.accessCode)) updateBadge(); }, 2600);
  }
  fetchConfig();
  show(state.setupDone ? "home" : "welcome");
}

window.addEventListener("hashchange", () => {
  const h = (location.hash || "").replace("#/", "");
  if (routes[h]) show(h);
});

boot();
