// Shared i18n core. Kept intentionally tiny: label maps used by both surfaces.
export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "hi-latn", label: "Hinglish" },
];

export const MODE_BADGE = {
  practice: "Practice mode: no microphone, no credits",
  live: "Live mode",
};

export function langLabel(code) {
  const hit = LANGUAGES.find((l) => l.code === code);
  return hit ? hit.label : code;
}
