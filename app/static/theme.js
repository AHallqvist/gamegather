"use strict";

(() => {
  // Named palettes live in styles.css. Add future themes here to expose them
  // in the selector; System is a preference, not a separate palette.
  const themes = [
    { id: "light", label: "Light" },
    { id: "dark", label: "Dark" },
  ];
  const storageKey = "gamegather.theme";
  const root = document.documentElement;
  const systemDark = typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-color-scheme: dark)")
    : null;
  let selector;

  function normalize(value) {
    return themes.some((theme) => theme.id === value) ? value : "system";
  }

  let preference = "system";
  try {
    preference = normalize(window.localStorage.getItem(storageKey));
  } catch {
    // Storage may be disabled. Switching still works for the current page.
  }

  function apply() {
    root.dataset.theme = preference === "system"
      ? (systemDark?.matches ? "dark" : "light")
      : preference;
    if (selector) selector.value = preference;
  }

  // This script intentionally runs before the stylesheet, without defer/async,
  // so a saved preference is applied before the first styled paint.
  apply();

  function initializeSelector() {
    selector = document.querySelector("[data-theme-select]");
    const picker = document.querySelector("[data-theme-picker]");
    if (!selector || !picker) return;
    for (const theme of [{ id: "system", label: "System" }, ...themes]) {
      const option = document.createElement("option");
      option.value = theme.id;
      option.textContent = theme.label;
      selector.append(option);
    }
    selector.value = preference;
    selector.addEventListener("change", () => {
      preference = normalize(selector.value);
      apply();
      try {
        window.localStorage.setItem(storageKey, preference);
      } catch {
        // Do not discard the current selection when storage is unavailable.
      }
    });
    picker.hidden = false;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeSelector, { once: true });
  } else {
    initializeSelector();
  }

  function followSystem() {
    if (preference === "system") apply();
  }
  if (systemDark?.addEventListener) {
    systemDark.addEventListener("change", followSystem);
  } else if (systemDark?.addListener) {
    systemDark.addListener(followSystem);
  }

  window.addEventListener("storage", (event) => {
    if (event.key === storageKey || event.key === null) {
      preference = normalize(event.newValue);
      apply();
    }
  });
})();
