# CallEye — Frontend System Design

A clean, easy-to-use interface guide for the CallEye PWA. This document is the
source of truth for the frontend. Everything on screen follows it.

## 1. Design principles

1. **Calm and trustworthy.** CallEye helps people in a stressful moment. The UI
   is quiet, ordered, and institutional — like a bank or a government service —
   never playful, never flashing, never alarming.
2. **One job per page.** Each screen has exactly one task. Content is split into
   pages; it is never jumbled into one long scroll.
3. **Mobile-first.** The app is used on a phone held next to a speakerphone.
   Every layout works from 320px wide.
4. **Honest by design.** Copy follows the safety rule: green = "no warning signs
   so far", never "safe". Red is calm, short, and actionable.

## 2. Pages (screens)

The app is a single-page app (SPA): one HTML shell, several `<main>` screens,
shown one at a time via JS.

| Screen id | Purpose | Nav |
| --- | --- | --- |
| `login` | **Demo gate** — the app is restricted to test/demo calls; a passcode unlocks the demo. Real user accounts would need a database + backend auth. | Always first |
| `landing` | **Home** — hero, how-to-use in 3 steps, language, and a **demo grid** (multiple scripted calls, default English). Time to first action < 5s. | Logo, "How it works" |
| `how` | **How it works** — the tutorial: pipeline, five signals, would-never-ask test, pressure meter, verdict levels, live demos. | "How it works" link |
| `listening` | Live session — pressure meter, stage chips, transcript, live colour. | — (full screen) |
| `verdict` | Result — green/amber/red card, verify-first actions, guardian notify. | — |
| `setup` | **Settings** — guardian, contacts, invite code, safe word. | ⚙️ button |
| `mictest` | Separate page — microphone check before scanning. | Reached from Home |

Navigation behaviour:
- Logo → Home always.
- Home & How-it-works are links in the top bar.
- ⚙️ opens Settings.
- Listening and Verdict are full-screen flow states; they hide nav to reduce
  distraction (use back/again buttons).

## 3. Design tokens (colour, type, shape)

### Colour
| Token | Value | Use |
| --- | --- | --- |
| `--navy-900` | `#091f40` | Primary background, top bar, primary buttons, headings |
| `--navy-800` | `#0b2a55` | Hover state for navy |
| `--blue` | `#1f5fe0` | Single accent — links, focus, highlights |
| `--ink` | `#0b2147` | Body text |
| `--muted` | `#56637a` | Secondary text |
| `--bg` | `#ffffff` | Page background |
| `--bg-alt` | `#f5f8fb` | Subtle panel/well background |
| `--line` | `#dfe6ef` | Hairline borders |
| `--green` / `--amber` / `--red` | `#0e8a5c` / `#a45309` / `#c0352e` | Verdict colours (three calm levels) |

Background depth: the page uses a **very subtle** radial wash in the top corners
(white with a faint navy/blue tint) so it is not flat white, but stays calm and
legible. No strong gradients, no noise textures.

### Typography
| Role | Font | Weight |
| --- | --- | --- |
| Headings (h1–h3) | Space Grotesk | 600 |
| Body & UI | Inter | 400/500/600 |

- Body 16px, line-height 1.5.
- Headings tight letter-spacing (-0.02em), sizes: h1 32–42px, h2 24px, h3 19px.

### Shape & elevation
- **All corners square (radius 0).** This gives the institutional, secure feel.
- Elevation is **hairline borders + a single left accent bar** (3–4px navy or
  verdict colour), not drop shadows. Shadows are used only for hover micro-lift.
- Buttons: flat navy (or white with navy border). Primary button has a 3px blue
  bottom edge (weight/anchoring).

## 4. Layout & navigation

**Top bar (sticky, navy):**
- Left: logo (white square mark + "CallEye" in Space Grotesk).
- Center/right: nav links — *Home*, *How it works* — in a muted white; status
  chip (Mock/Live); ⚙️ settings button.

**Mobile (≤700px):**
- Nav links collapse to compact width (fit 2 short labels + status chip + gear).
- Any multi-column grid (steps, pipeline, cards, scenarios) collapses to a single
  column. Dividers become horizontal.
- Touch targets ≥ 40px tall. Padding 16–20px.

**Flow:**
```
Home → Scan a call now → Listening → Verdict → again → Home
Home → Run a demo (on How-it-works) → Listening → Verdict
Home → ⚙️ → Setup → Save → Home
Home → Check my microphone → mic-test → back
```

## 5. Screen-by-screen

### Home (`landing`)
- Eyebrow (small navy pill): "Speakerphone safety companion".
- h1 + accent word, one calm subline.
- One primary CTA: **Scan a call now** (uses your live microphone). The mic
  check is a utility link in the footer — the demos are prerecorded, so the
  landing does not advertise the mic test.
- Language selector (inline, bordered well).
- The 3 numbered steps in a bordered row (01 Put it on speaker / 02 Reads the
  pressure / 03 You decide calmly).
- Footer: honesty note + links.

### How it works (`how`)
Split into clear cards, each with a navy/verdict top rule:
1. **How it works** — 4-step pipeline (Listen → Read signals → Score → Decide).
2. **The five pressure signals** — authority, fear, isolation, urgency, ask.
3. **The "would never ask" test** — the red-flag list.
4. **The pressure meter** — 0–100 weighted score, ~20s decay.
5. **How real calls are told apart** — green/amber/red meaning with dots.
6. **Live demos** — two scripted calls to try (scam → red, genuine → green).

### Listening (`listening`)
Full screen, one column: scenario bar, status, pressure meter (blue fill),
stage chips, live transcript, reasons, Stop/Speak actions.

### Verdict (`verdict`)
Single card with a colored top rule (green/amber/red), the verdict text, then
the *verify-first* panel (call 112, safe word) and *guardian* panel on red.
One clear "Listen again" action.

### Settings (`setup`)
Clean form sections: Guardian (name/phone), Trusted contacts, Invite code,
Family safe word note. One Save button.

### Microphone test (`mictest`)
- A short explanation.
- A large square level meter (blue fill) that reacts to sound.
- Start/Stop button.
- Back-to-Home link.

## 6. Content & wording rules
- Never say "safe" for green — always "no warning signs so far".
- Keep sentences short. Red verdicts are calm and terse.
- Use the real detector terms (pressure, signals, would-never-ask) so the UI
  teaches the model honestly.

## 7. Files
- `app/static/index.html` — SPA shell (all screens except mic-test).
- `app/static/styles.css` — single stylesheet (this system).
- `app/static/app.js` — screen switching + app logic.
- `app/static/mic-test.html` — standalone mic check page.
