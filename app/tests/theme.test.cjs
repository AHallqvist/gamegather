const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../static/theme.js"), "utf8");

function browser({ stored = null, dark = false, blocked = false, ready = false, media = true, script = source } = {}) {
  const documentEvents = {};
  const windowEvents = {};
  const selectorEvents = {};
  const writes = [];
  const picker = { hidden: true };
  const selector = {
    value: "", options: [],
    append(option) { this.options.push(option); },
    addEventListener(name, callback) { selectorEvents[name] = callback; },
  };
  const query = {
    matches: dark,
    addEventListener(name, callback) { this.listener = callback; },
  };
  const document = {
    documentElement: { dataset: {} },
    readyState: ready ? "complete" : "loading",
    querySelector: (query) => query === "[data-theme-select]" ? selector : picker,
    createElement: () => ({}),
    addEventListener(name, callback) { documentEvents[name] = callback; },
  };
  const window = {
    addEventListener(name, callback) { windowEvents[name] = callback; },
    localStorage: {
      getItem() { if (blocked) throw new Error("Storage blocked"); return stored; },
      setItem(key, value) { if (blocked) throw new Error("Storage blocked"); writes.push([key, value]); },
    },
  };
  if (media) window.matchMedia = () => query;
  vm.runInNewContext(script, { window, document });
  return {
    document, picker, selector, writes,
    theme: () => document.documentElement.dataset.theme,
    ready() { documentEvents.DOMContentLoaded(); },
    select(value) { selector.value = value; selectorEvents.change(); },
    system(dark) { query.matches = dark; query.listener(); },
    storage(key, newValue) { windowEvents.storage({ key, newValue }); },
  };
}

test("applies the system palette before the selector is available", () => {
  for (const dark of [false, true]) {
    const page = browser({ dark });
    assert.equal(page.theme(), dark ? "dark" : "light");
    assert.equal(page.picker.hidden, true);
    page.ready();
    assert.equal(page.picker.hidden, false);
    assert.equal(page.selector.value, "system");
    assert.deepEqual(page.selector.options.map((option) => option.value), ["system", "light", "dark"]);
  }
});

test("saved explicit preferences override the device on first load", () => {
  for (const stored of ["light", "dark"]) {
    const page = browser({ stored, dark: stored === "light" });
    assert.equal(page.theme(), stored);
    page.ready();
    assert.equal(page.selector.value, stored);
    page.system(stored !== "dark");
    assert.equal(page.theme(), stored);
  }
});

test("unknown, removed, and System preferences fall back to System", () => {
  for (const stored of [null, "system", "removed-theme", "DARK", "", "__proto__"]) {
    const page = browser({ stored, dark: true });
    page.ready();
    assert.equal(page.selector.value, "system");
    assert.equal(page.theme(), "dark");
    page.system(false);
    assert.equal(page.theme(), "light");
  }
});

test("selection applies immediately, persists, and resumes following System", () => {
  const page = browser();
  page.ready();
  page.select("dark");
  assert.equal(page.theme(), "dark");
  assert.deepEqual(page.writes[0], ["gamegather.theme", "dark"]);
  const reloaded = browser({ stored: page.writes[0][1] });
  assert.equal(reloaded.theme(), "dark");
  page.system(false);
  assert.equal(page.theme(), "dark");
  page.select("light");
  assert.equal(page.theme(), "light");
  page.system(true);
  assert.equal(page.theme(), "light");
  page.select("system");
  assert.equal(page.theme(), "dark");
  page.system(false);
  assert.equal(page.theme(), "light");
  assert.deepEqual(page.writes.at(-1), ["gamegather.theme", "system"]);
});

test("blocked storage does not prevent initialization or current-page switching", () => {
  const page = browser({ blocked: true, dark: true });
  page.ready();
  assert.equal(page.selector.value, "system");
  page.select("light");
  assert.equal(page.theme(), "light");
  page.system(true);
  assert.equal(page.theme(), "light");
});

test("initializes if the DOM is already ready and handles unavailable matchMedia", () => {
  const page = browser({ ready: true, media: false });
  assert.equal(page.theme(), "light");
  assert.equal(page.picker.hidden, false);
  page.select("dark");
  assert.equal(page.theme(), "dark");
});

test("synchronizes other tabs and resets to System when storage is cleared", () => {
  const page = browser({ ready: true, dark: true });
  page.storage("gamegather.theme", "light");
  assert.equal(page.theme(), "light");
  assert.equal(page.selector.value, "light");
  page.storage("unrelated", "dark");
  assert.equal(page.theme(), "light");
  page.storage(null, null);
  assert.equal(page.theme(), "dark");
  assert.equal(page.selector.value, "system");
});

test("Dark and the no-JavaScript system fallback have matching complete palettes", () => {
  const css = fs.readFileSync(path.join(__dirname, "../static/styles.css"), "utf8");
  const declarations = (selector) => {
    const body = css.slice(css.indexOf(selector)).match(/\{([^}]+)\}/)[1];
    return Object.fromEntries([...body.matchAll(/(--[\w-]+|color-scheme):\s*([^;]+);/g)]
      .map((match) => [match[1], match[2].trim()]));
  };
  const light = declarations(":root {");
  const dark = declarations(':root[data-theme="dark"]');
  assert.deepEqual(Object.keys(dark).sort(), Object.keys(light).sort());
  assert.deepEqual(declarations(":root:not([data-theme])"), dark);
});

test("future named themes use the same registry, persistence, and device override behavior", () => {
  const script = source.replace(
    '{ id: "dark", label: "Dark" },',
    '{ id: "dark", label: "Dark" }, { id: "colorful", label: "Colorful" },',
  );
  const page = browser({ script, stored: "colorful", ready: true });
  assert.equal(page.theme(), "colorful");
  assert.equal(page.selector.value, "colorful");
  assert.equal(page.selector.options.at(-1).textContent, "Colorful");
  page.system(true);
  assert.equal(page.theme(), "colorful");
  page.select("system");
  assert.equal(page.theme(), "dark");
  page.select("colorful");
  assert.deepEqual(page.writes.at(-1), ["gamegather.theme", "colorful"]);
});
