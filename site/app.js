// CallEye landing behaviour. Public: no login, no microphone, no service worker.
import { createDemoEngine } from "/shared/result-view.js";

const resultEl = document.getElementById("demoResult");
const engine = createDemoEngine(resultEl);
let activeRun = null;

function playFixture(name) {
  // Sample audio / captions run only after a tap (the Play button). No autoplay.
  fetch("/data/fixtures/" + name + ".json")
    .then((r) => {
      if (!r.ok) throw new Error("missing fixture");
      return r.json();
    })
    .then((fixture) => {
      const expectNote = fixture.label === "genuine" ? "stays green"
        : fixture.label === "emergency" ? "shows the verify-first screen"
        : "amber then red";
      if (activeRun) activeRun.stop();
      activeRun = engine.play(fixture.segments, {
        title: fixture.id.replace("demo_", "").replace(/_/g, " "),
        expect: expectNote,
        speed: 1.4,
      });
    })
    .catch(() => {
      resultEl.innerHTML = '<p class="result-empty">Sorry — this sample is not available.</p>';
    });
}

document.querySelectorAll(".sample").forEach((card) => {
  const btn = card.querySelector(".run-sample");
  const fixture = card.dataset.fixture;
  btn.addEventListener("click", () => playFixture(fixture));
});

// Evaluation section: only if a report exists (site/data/eval.json). Never placeholder.
const evalSection = document.getElementById("evalSection");
fetch("/data/eval.json")
  .then((r) => {
    if (!r.ok) throw new Error("no eval report");
    return r.json();
  })
  .then((data) => {
    const body = document.getElementById("evalBody");
    let html = "<table><tbody>";
    Object.entries(data.metrics || {}).forEach(([k, v]) => {
      html += "<tr><th>" + k + "</th><td>" + v + "</td></tr>";
    });
    html += "</tbody></table>";

    if (data.misclassifications && data.misclassifications.length) {
      html += "<p style='margin-top:10px'><strong>Misclassifications:</strong> " +
        data.misclassifications.join(", ") + "</p>";
    }
    body.innerHTML = html;
    evalSection.classList.remove("hidden");
  })
  .catch(() => {
    evalSection.classList.add("hidden");
  });
