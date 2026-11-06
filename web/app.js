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
  auth: $("#view-auth"),
  authTitle: $("#authTitle"),
  authName: $("#authName"),
  authEmail: $("#authEmail"),
  authPassword: $("#authPassword"),
  authMsg: $("#authMsg"),
  authSubmit: $("#authSubmit"),
  authToggle: $("#authToggle"),
  modeBadge: $("#modeBadge"),
  settingsHint: $("#settingsHint"),
  welcomeStart: $("#welcomeStart"),
  setupSave: $("#setupSave"),
  practiceBtn: $("#practiceBtn"),
  liveBtn: $("#liveBtn"),
  uploadBtn: $("#uploadBtn"),
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
  setName: $("#setName"),
  setEmail: $("#setEmail"),
  setGName: $("#setGName"),
  setGPhone: $("#setGPhone"),
  setTheme: $("#setTheme"),
  setProfileSave: $("#setProfileSave"),
  setGuardianSave: $("#setGuardianSave"),
  profileMsg: $("#profileMsg"),
  guardianMsg: $("#guardianMsg"),
};

const routes = {
  auth: "view-auth",
  welcome: "view-welcome",
  setup: "view-setup",
  home: "view-home",
  practice: "view-practice",
  live: "view-live",
  upload: "view-upload",
  settings: "view-settings",
};

const state = {
  setupDone: !!localStorage.getItem("calleye.setup"),
  accessCode: localStorage.getItem("calleye.access_code") || "",
  liveEnabled: false,
  dailyCap: 0,
  lang: "en",
  token: localStorage.getItem("calleye.token") || "",
  user: null,
  authMode: "login", // "login" | "signup"
};

// Fetch wrapper that attaches the bearer token.
function authedFetch(url, opts) {
  opts = opts || {};
  opts.headers = Object.assign({}, opts.headers || {});
  if (state.token) opts.headers["Authorization"] = "Bearer " + state.token;
  return fetch(url, opts);
}

function show(name) {
  Object.values(routes).forEach((id) => $("#" + id).classList.add("hidden"));
  $("#" + routes[name]).classList.remove("hidden");
  setActiveNav(name);
  if (name === "settings") openSettings();
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
  setRailState();
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

// ---- auth (login / signup) ----
function setAuthMode(mode) {
  state.authMode = mode;
  els.authTitle.textContent = mode === "signup" ? "Create your account" : "Log in to CallEye";
  els.authSubmit.textContent = mode === "signup" ? "Sign up" : "Log in";
  els.authToggle.textContent = mode === "signup" ? "Already have an account? Log in" : "Need an account? Sign up";
  els.authName.closest("label").style.display = mode === "signup" ? "" : "none";
  els.authMsg.textContent = "";
  els.authMsg.className = "msg";
}

async function submitAuth() {
  const email = els.authEmail.value.trim();
  const password = els.authPassword.value;
  const name = els.authName.value.trim();
  if (!email || !password) {
    els.authMsg.textContent = "Email and password are required.";
    els.authMsg.className = "msg err";
    return;
  }
  if (state.authMode === "signup" && !name) {
    els.authMsg.textContent = "Please enter your name.";
    els.authMsg.className = "msg err";
    return;
  }
  const path = state.authMode === "signup" ? "/api/auth/signup" : "/api/auth/login";
  const body = { email, password };
  if (state.authMode === "signup") body.name = name;
  try {
    const r = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok) {
      els.authMsg.textContent = j.detail || "Something went wrong.";
      els.authMsg.className = "msg err";
      return;
    }
    state.token = j.token;
    state.user = j.user;
    localStorage.setItem("calleye.token", j.token);
    populateProfile();
    populateGuardian();
    show("home");
  } catch (e) {
    els.authMsg.textContent = "Network error. Try again.";
    els.authMsg.className = "msg err";
  }
}

function logout() {
  if (state.token) {
    fetch("/api/auth/logout", { method: "POST", headers: { Authorization: "Bearer " + state.token } })
      .catch(() => {});
  }
  state.token = "";
  state.user = null;
  localStorage.removeItem("calleye.token");
  setAuthMode("login");
  show("auth");
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

  authedFetch("/api/practice/demo_digital_arrest", { method: "POST" })
    .then((r) => {
      if (r.status === 401) { logout(); throw new Error("please log in"); }
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
      token: state.token,
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
    const r = await authedFetch("/api/transcribe", { method: "POST", body: fd });
    if (r.status === 401) { logout(); return; }
    const j = await r.json();
    els.uploadOut.innerHTML =
      "<strong>Level:</strong> " + (j.level || "?") +
      " &nbsp; <strong>Pressure:</strong> " + (j.pressure || 0) +
      (j.transcript ? "<br><strong>Transcript:</strong> " + j.transcript : "");
  } catch (e) {
    els.uploadOut.textContent = "Could not analyse that file.";
  }
}

// ---- dashboard shell (sidebar + profile + rail) ----
function buildSidebar() {
  const tpl = document.getElementById("sideTpl");
  if (!tpl) return;
  document.querySelectorAll("[data-side]").forEach((host) => {
    host.innerHTML = tpl.innerHTML;
  });
}

function setActiveNav(name) {
  const valid = { home: 1, practice: 1, live: 1, upload: 1, settings: 1 };
  document.querySelectorAll(".nav-item[data-nav]").forEach((n) => {
    n.classList.toggle("active", !!valid[name] && n.dataset.nav === name);
  });
}

function setRailState() {
  const live = !!(state.liveEnabled && state.accessCode);
  const badge = document.getElementById("railModeBadge");
  const hint = document.getElementById("railModeHint");
  const sub = document.getElementById("liveCardSub");
  if (badge) {
    badge.textContent = live ? MODE_BADGE.live : MODE_BADGE.practice;
    badge.classList.toggle("live", live);
  }
  if (hint) {
    hint.textContent = live
      ? "Live is unlocked — you can analyse real calls."
      : (state.liveEnabled ? "Needs an access code from your organiser." : "Live mode is off right now.");
  }
  if (sub) {
    sub.textContent = live
      ? "Unlocked — start listening."
      : (state.liveEnabled ? "Needs an access code from your organiser." : "Live mode is off right now.");
  }
}

function populateProfile() {
  const name = (state.user && state.user.name) || "Guest";
  const email = (state.user && state.user.email) || "";
  const initials = name.split(/\s+/).slice(0, 2).map((s) => s.charAt(0)).join("").toUpperCase() || "?";
  document.querySelectorAll(".user-name").forEach((el) => { el.textContent = name; });
  document.querySelectorAll(".user-mail").forEach((el) => { el.textContent = email; });
  document.querySelectorAll(".avatar").forEach((el) => { el.textContent = initials; });
}

function populateGuardian() {
  let g = null;
  try { g = JSON.parse(localStorage.getItem("calleye.guardian") || "null"); } catch (e) { /* ignore */ }
  const line = document.getElementById("guardianLine");
  if (!line) return;
  if (g && (g.name || g.phone)) {
    line.textContent = [g.name, g.phone].filter(Boolean).join(" · ");
  } else {
    line.textContent = "Not set up yet.";
  }
}

// ---- appearance (dark mode) ----
function applyTheme(dark) {
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  localStorage.setItem("calleye.theme", dark ? "dark" : "light");
  if (els.setTheme) els.setTheme.checked = !!dark;
}
function initTheme() {
  applyTheme(localStorage.getItem("calleye.theme") === "dark");
}

// ---- settings screen ----
function openSettings() {
  const name = (state.user && state.user.name) || "";
  const email = (state.user && state.user.email) || "";
  els.setName.value = name;
  els.setEmail.value = email;
  let g = null;
  try { g = JSON.parse(localStorage.getItem("calleye.guardian") || "null"); } catch (e) { /* ignore */ }
  els.setGName.value = (g && g.name) || "";
  els.setGPhone.value = (g && g.phone) || "";
  els.setTheme.checked = document.documentElement.getAttribute("data-theme") === "dark";
}

async function saveProfile() {
  const name = els.setName.value.trim();
  if (!name) { els.profileMsg.textContent = "Name cannot be empty."; els.profileMsg.className = "msg err"; return; }
  els.profileMsg.textContent = "Saving…";
  els.profileMsg.className = "msg";
  try {
    const r = await authedFetch("/api/auth/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (r.status === 401) { logout(); return; }
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || "save failed");
    state.user = j.user;
    populateProfile();
    els.profileMsg.textContent = "Profile updated.";
    els.profileMsg.className = "msg ok";
  } catch (e) {
    els.profileMsg.textContent = "Could not save. Try again.";
    els.profileMsg.className = "msg err";
  }
}

function saveGuardian() {
  const name = els.setGName.value.trim();
  const phone = els.setGPhone.value.trim();
  if (name || phone) {
    localStorage.setItem("calleye.guardian", JSON.stringify({ name, phone }));
  } else {
    localStorage.removeItem("calleye.guardian");
  }
  populateGuardian();
  els.guardianMsg.textContent = "Guardian saved on this device.";
  els.guardianMsg.className = "msg ok";
}

document.addEventListener("click", (e) => {
  const nav = e.target.closest(".nav-item[data-nav]");
  if (nav) {
    // "Go live" must respect the same live gate as the Home button:
    // live-off -> hint, locked -> unlock sheet, unlocked -> start.
    if (nav.dataset.nav === "live") {
      setActiveNav("live");
      if (!state.liveEnabled) {
        els.settingsHint.textContent = "Live mode is off right now.";
        return;
      }
      if (!state.accessCode) { openUnlock(); } else { startLive(); }
      return;
    }
    show(nav.dataset.nav);
    return;
  }
  if (e.target.closest(".js-logout")) { logout(); }
});

// ---- events ----
els.welcomeStart.addEventListener("click", () => show("setup"));
els.setupSave.addEventListener("click", () => {
  const gName = els.gName.value.trim();
  const gPhone = els.gPhone.value.trim();
  if (gName || gPhone) {
    localStorage.setItem("calleye.guardian", JSON.stringify({ name: gName, phone: gPhone }));
  }
  localStorage.setItem("calleye.setup", "1");
  state.setupDone = true;
  populateGuardian();
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
els.setProfileSave.addEventListener("click", saveProfile);
els.setGuardianSave.addEventListener("click", saveGuardian);
els.setTheme.addEventListener("change", () => applyTheme(els.setTheme.checked));
els.authSubmit.addEventListener("click", submitAuth);
els.authToggle.addEventListener("click", () => setAuthMode(state.authMode === "signup" ? "login" : "signup"));
els.authPassword.addEventListener("keydown", (e) => { if (e.key === "Enter") submitAuth(); });

// Register the service worker ONLY from the app (scope /app/). The landing
// never registers a service worker.
if ("serviceWorker" in navigator && location.pathname.startsWith("/app")) {
  navigator.serviceWorker.register("/app/sw.js", { scope: "/app/" }).catch(() => {});
}

// ---- boot ----
function boot() {
  initTheme();
  buildSidebar();
  // Direct-access mode: only practice + upload. Hide live and login entry points.
  const liveNav = document.querySelector('[data-nav="live"]');
  if (liveNav) liveNav.classList.add("hidden");
  const liveBtn = document.getElementById("liveBtn");
  if (liveBtn) { const card = liveBtn.closest(".action-card"); if (card) card.classList.add("hidden"); }
  const logoutBtn = document.querySelector(".js-logout");
  if (logoutBtn) logoutBtn.classList.add("hidden");
  populateGuardian();
  const wasFast = checkWake();
  if (!wasFast) {
    els.modeBadge.textContent = "Waking up the app, one moment";
    setTimeout(() => { if (!(state.liveEnabled && state.accessCode)) updateBadge(); }, 2600);
  }
  fetchConfig();
  populateProfile();
  show("home");
}

window.addEventListener("hashchange", () => {
  const h = (location.hash || "").replace("#/", "");
  if (routes[h]) show(h);
});

boot();
