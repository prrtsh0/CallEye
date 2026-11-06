// Shared result view + demo engine.
// Used by BOTH the public landing demo and the app (no duplication).
// The engine runs locally from fixture segments: nothing is transmitted, the
// "flagged N seconds before the ask" figure is computed from the fixture data.

export const STAGES = ["Authority", "Fear", "Isolation", "Urgency", "Ask"];

// ---- lightweight keyword rules (mirror DETECTOR.md, simplified & honest) ----
const AUTHORITY = ["police", "station", "court", "government", "cbi", "income tax", "customs"];
const FEAR = ["arrest", "case", "blocked", "serious", "legal", "jail", "trouble", "stop work"];
const ISOLATION = ["don't tell", "do not tell", "tell anyone", "no one", "secret", "mat batana", "kisi ko nahi", "koi nahi"];
const URGENCY = ["immediately", "right now", "today", "deadline", "hurry", "too late", "turant", "abhi", "der"];
const ASK = ["otp", "pin", "cvv", "upi", "password", "transfer", "pay", "payment", "fee", "safe account", "install app", "cash", "rupees", "money"];
const EMERGENCY = ["injured", "kidnapped", "kidnap", "accident", "hospital", "arrested", "dukhad"];
const WARN = ["never", "do not", "don't", "mat", "nahi", "kabhi nahi", "kabhi"];

function hasAny(text, words) {
  return words.some((w) => text.includes(w));
}

function classifySegment(text) {
  const t = text.toLowerCase();
  const stages = [];
  if (hasAny(t, AUTHORITY)) stages.push("Authority");
  if (hasAny(t, FEAR)) stages.push("Fear");
  if (hasAny(t, ISOLATION)) stages.push("Isolation");
  if (hasAny(t, URGENCY)) stages.push("Urgency");
  const isAsk = hasAny(t, ASK);
  const isEmergency = hasAny(t, EMERGENCY);
  const isWarning = hasAny(t, WARN) && isAsk; // "never share OTP" => warning
  if (isAsk) stages.push("Ask");
  return { stages, isAsk, isEmergency, isWarning };
}

// ---- view: builds the shared result UI into a container ----
export function createResultView(container) {
  container.classList.add("rv");
  container.innerHTML = `
    <div class="rv-scenario" aria-live="polite"></div>
    <div class="rv-meter">
      <div class="rv-meter-label">Pressure</div>
      <div class="rv-meter-track"><div class="rv-meter-fill"></div></div>
      <div class="rv-meter-value">0</div>
    </div>
    <div class="rv-chips"></div>
    <div class="rv-transcript"></div>
    <div class="rv-status"></div>
    <div class="rv-verify hidden">
      <h3>Check before you act</h3>
      <p>Call a number you already have. Do not use the number the caller gives you.</p>
    </div>
    <button class="rv-log" hidden></button>`;

  const q = (sel) => container.querySelector(sel);
  const chipsEl = q(".rv-chips");
  const transcriptEl = q(".rv-transcript");
  const statusEl = q(".rv-status");
  const meterFill = q(".rv-meter-fill");
  const meterValue = q(".rv-meter-value");
  const scenarioEl = q(".rv-scenario");

  STAGES.forEach((name) => {
    const c = document.createElement("div");
    c.className = "rv-chip";
    c.textContent = name;
    c.dataset.stage = name;
    chipsEl.appendChild(c);
  });
  const chips = Array.from(chipsEl.querySelectorAll(".rv-chip"));

  const setLevelClass = (level) => {
    container.classList.remove("rv-green", "rv-amber", "rv-red");
    if (level) container.classList.add("rv-" + level);
  };

  return {
    setScenario(title) { scenarioEl.textContent = title; },
    setStages(active) {
      chips.forEach((c) => c.classList.toggle("on", active.includes(c.dataset.stage)));
    },
    setPressure(v) {
      const clamped = Math.max(0, Math.min(100, Math.round(v)));
      meterFill.style.width = clamped + "%";
      meterValue.textContent = clamped;
    },
    appendCaption(text, final) {
      const div = document.createElement("div");
      div.textContent = text;
      if (final) div.classList.add("final");
      transcriptEl.appendChild(div);
      transcriptEl.scrollTop = transcriptEl.scrollHeight;
    },
    setStatus(text) { statusEl.textContent = text; },
    setLevel(level) { setLevelClass(level); },
    showVerify(show) { q(".rv-verify").classList.toggle("hidden", !show); },
    reset() {
      transcriptEl.innerHTML = "";
      statusEl.textContent = "";
      this.setPressure(0);
      this.setStages([]);
      this.setLevel(null);
      this.showVerify(false);
    },
  };
}

// ---- demo engine: plays fixture segments through a view ----
export function createDemoEngine(container) {
  const view = createResultView(container);
  let timers = [];
  let cancelled = false;
  let askT = null;
  let alertT = null;
  let pressure = 0;

  const reset = () => {
    timers.forEach(clearTimeout);
    timers = [];
    cancelled = false;
    askT = null;
    alertT = null;
    pressure = 0;
    view.reset();
  };

  const levelFor = () => {
    if (pressure >= 70) return "red";
    if (pressure >= 40) return "amber";
    return "green";
  };

  // Run the stored sample call. `speed` scales each segment's timestamp.
  function play(segments, opts = {}) {
    reset();
    view.setScenario(opts.title || "Sample call");
    const speed = opts.speed || 1;
    if (opts.expect) container.dataset.expect = opts.expect;

    let redForced = false;
    let amberForced = false;
    let emergencySeen = false;
    let moneySeen = false;
    let isolateSeen = false;

    segments.forEach((seg, i) => {
      const delay = seg.t * 1000 / speed;
      timers.push(setTimeout(() => {
        if (cancelled) return;
        const c = classifySegment(seg.text);
        view.appendCaption(seg.text, true);
        view.setStages(c.stages);

        // accumulate pressure
        const w = c.stages.length * 6 + (c.isAsk ? 16 : 0) + (c.isWarning ? -8 : 0);
        pressure = Math.max(0, Math.min(100, pressure + Math.max(0, w)));
        view.setPressure(pressure);

        if (c.isEmergency) emergencySeen = true;
        if (c.isAsk && !c.isWarning) moneySeen = true;
        if (c.stages.includes("Isolation")) isolateSeen = true;

        // would-never-ask => red
        if (c.isAsk && !c.isWarning && (hasAny(seg.text.toLowerCase(), ["otp", "pin", "cvv", "upi", "password", "transfer", "payment", "pay", "money", "cash"]))) {
          redForced = true;
        }
        // emergency claim: default amber; red only with money + isolation/urgency
        if (emergencySeen && moneySeen && isolateSeen) {
          redForced = true;
        } else if (emergencySeen) {
          amberForced = true;
        }

        let level = levelFor();
        if (redForced) level = "red";
        else if (amberForced) level = "amber";
        view.setLevel(level);
        view.showVerify(level === "amber" || level === "red");

        if (c.isAsk && !c.isWarning && askT === null) askT = delay / 1000;
        if (alertT === null && level !== "green") alertT = delay / 1000;

        // flagged-before-ask, computed from the fixture (negative diff => alerted before ask)
        if (askT !== null && alertT !== null) {
          const diff = alertT - askT;
          view.setStatus(
            diff <= 0
              ? "Flagged " + Math.round(-diff) + "s before the ask"
              : "Warned after the ask"
          );
        }
      }, delay));
    });

    return {
      stop() { cancelled = true; timers.forEach(clearTimeout); },
    };
  }

  return { view, play };
}
