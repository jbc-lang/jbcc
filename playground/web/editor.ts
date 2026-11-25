type SourceFile = { path: string; source: string };
type Project = { files: SourceFile[]; entry: string; units: string[] };
type Draft = Project & { active: string; stdin: string };
type Diagnostic = {
  path?: string;
  line?: number;
  column?: number;
  severity: string;
  message: string;
};
type Build = { diagnostics: Diagnostic[]; javascript?: string; wasm?: string };
type RunEvent =
  | { type: "stdout" | "stderr"; text: string }
  | { type: "exit"; status: number }
  | { type: "error"; message: string };
type Activity = {
  request: AbortController;
  stopRunner?: () => void;
};

function element<T extends HTMLElement>(id: string): T {
  return document.getElementById(id) as T;
}

const tabs = element("tabs");
const editor = element<HTMLTextAreaElement>("source");
const lines = element("lines");
const filename = element<HTMLInputElement>("filename");
const entrySelect = element<HTMLSelectElement>("entry");
const unit = element<HTMLInputElement>("unit");
const examples = element<HTMLSelectElement>("example");
const remove = element<HTMLButtonElement>("remove");
const stdin = element<HTMLTextAreaElement>("stdin");
const stdout = element("stdout");
const stderr = element("stderr");
const status = element("status");
const box = element("diagnostics");
const theme = element<HTMLButtonElement>("theme");
const buildButton = element<HTMLButtonElement>("build");
const runButton = element<HTMLButtonElement>("run");
const stopButton = element<HTMLButtonElement>("stop");

const draftKey = "jbcc.playground.draft";
const themeKey = "jbcc.playground.theme";
const exampleFiles = {
  hello: ["hello.b"],
  status: ["caller.b", "get.status.b", "I_STATUS"],
};

function getStorage(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function putStorage(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // The editor still works when browser storage is unavailable.
  }
}

function loadDraft(): Draft | null {
  try {
    const item = JSON.parse(getStorage(draftKey) ?? "null");
    if (item?.files?.length && item.files.some((f: SourceFile) => f.path === item.active)) {
      return item;
    }
  } catch {
    // Open a new workspace if browser storage cannot be read.
  }
  return null;
}

const saved = loadDraft();
let draft: Draft = saved ?? {
  files: [{ path: "main.b", source: "" }],
  entry: "main.b",
  units: [],
  active: "main.b",
  stdin: "",
};
let activity: Activity | null = null;
let cached: { source: string; reply: Build } | undefined;
const views = new Map<string, { start: number; end: number; top: number; left: number }>();

function current(): SourceFile {
  return draft.files.find((file) => file.path === draft.active)!;
}

function save() {
  putStorage(draftKey, JSON.stringify(draft));
}

function numberLines() {
  const count = editor.value.split("\n").length;
  lines.textContent = Array.from({ length: count }, (_, i) => i + 1).join("\n");
  lines.scrollTop = editor.scrollTop;
}

function captureView() {
  views.set(draft.active, {
    start: editor.selectionStart, end: editor.selectionEnd,
    top: editor.scrollTop, left: editor.scrollLeft,
  });
}

function switchTab(path: string) {
  captureView();
  draft.active = path;
  render();
  save();
}

function button(text: string, action: () => void) {
  const control = document.createElement("button");
  control.type = "button";
  control.textContent = text;
  control.addEventListener("click", action);
  return control;
}

function render() {
  const file = current();
  tabs.replaceChildren();
  entrySelect.replaceChildren();
  for (const tab of draft.files) {
    const trigger = button(tab.path, () => switchTab(tab.path));
    trigger.setAttribute("aria-pressed", String(tab === file));
    tabs.append(trigger);
    entrySelect.add(new Option(tab.path, tab.path));
  }
  const add = button("+", newFile);
  add.setAttribute("aria-label", "New file");
  tabs.append(add);
  filename.value = file.path;
  entrySelect.value = draft.entry;
  unit.checked = draft.units.includes(file.path);
  unit.disabled = file.path === draft.entry;
  remove.disabled = draft.files.length === 1;
  editor.value = file.source;
  const view = views.get(file.path);
  editor.setSelectionRange(view?.start ?? 0, view?.end ?? 0);
  editor.scrollTop = view?.top ?? 0;
  editor.scrollLeft = view?.left ?? 0;
  numberLines();
}

function clearResult() {
  showDiagnostics([]);
  stdout.textContent = "";
  stderr.textContent = "";
}

function newFile() {
  let i = 1;
  while (draft.files.some((file) => file.path === `new-${i}.b`)) i++;
  const path = `new-${i}.b`;
  draft.files.push({ path, source: "" });
  switchTab(path);
  filename.focus();
  filename.select();
}

function rename() {
  const old = draft.active;
  const path = filename.value.trim();
  if (path === old) return;
  const parts = path.split("/");
  if (path.startsWith("-") ||
      parts.some((part) => !/^[a-zA-Z0-9_.-]+$/.test(part) || part === "." || part === "..") ||
      draft.files.some((file) => file.path === path)) {
    filename.value = old;
    status.textContent = "Enter a unique relative file path";
    return;
  }
  captureView();
  const view = views.get(old)!;
  views.delete(old);
  views.set(path, view);
  current().path = path;
  draft.active = path;
  if (draft.entry === old) draft.entry = path;
  draft.units = draft.units.map((name) => name === old ? path : name);
  render();
  save();
}

async function loadExample(key: keyof typeof exampleFiles) {
  const before = JSON.stringify(draft);
  status.textContent = "Loading example…";
  try {
    const files = await Promise.all(exampleFiles[key].map(async (path) => {
      const response = await fetch(`/examples/${path}`);
      if (!response.ok) throw new Error("Could not load example");
      return { path, source: await response.text() };
    }));
    if (activity || JSON.stringify(draft) !== before) {
      if (!activity) status.textContent = "Draft kept because it changed while loading";
      return;
    }
    draft = {
      files,
      entry: files[0].path,
      active: files[0].path,
      units: key === "status" ? [files[1].path] : [],
      stdin: "",
    };
    views.clear();
    stdin.value = "";
    render();
    save();
    clearResult();
    status.textContent = "Ready";
  } catch {
    if (!activity) status.textContent = "Could not load example";
  }
}

function showDiagnostics(items: Diagnostic[]) {
  box.replaceChildren();
  box.hidden = items.length === 0;
  for (const item of items) {
    const row = document.createElement("p");
    row.dataset.severity = item.severity;
    const { path, line, column } = item;
    if (path && line && draft.files.some((file) => file.path === path)) {
      row.append(button(`${path}:${line}:${column ?? 1}`, () => {
        if (!draft.files.some((file) => file.path === path)) return;
        switchTab(path);
        const sourceLines = editor.value.split("\n");
        const previous = sourceLines.slice(0, line - 1);
        const prefix = Array.from(sourceLines[line - 1] ?? "").slice(0, (column ?? 1) - 1).join("");
        const start = previous.reduce((n, value) => n + value.length + 1, 0) + prefix.length;
        editor.focus();
        editor.setSelectionRange(start, start);
        editor.scrollTop = Math.max(0, line - 3) * parseFloat(getComputedStyle(editor).lineHeight);
        lines.scrollTop = editor.scrollTop;
      }), " ");
    }
    row.append(item.message);
    box.append(row);
  }
}

function setActivity(value: Activity | null) {
  activity = value;
  buildButton.disabled = runButton.disabled = examples.disabled = value !== null;
  stopButton.disabled = value === null;
}

function startRunner(op: Activity, javascript: string, wasm: string, input: string) {
  const frame = document.createElement("iframe");
  frame.hidden = true;
  frame.title = "Isolated jBC runner";
  frame.sandbox.add("allow-scripts");
  const { port1, port2 } = new MessageChannel();
  const guard = window.setTimeout(() => finish("The browser runner did not respond"), 7000);

  function dispose() {
    window.clearTimeout(guard);
    port1.close();
    port2.close();
    frame.remove();
  }

  function finish(message: string) {
    dispose();
    if (activity === op) {
      status.textContent = message;
      setActivity(null);
    }
  }

  op.stopRunner = dispose;
  port1.onmessage = ({ data }: MessageEvent<RunEvent>) => {
    if (activity !== op) return;
    switch (data.type) {
      case "stdout": stdout.append(data.text); break;
      case "stderr": stderr.append(data.text); break;
      case "exit": finish(`Exited with status ${data.status}`); break;
      case "error": finish(data.message); break;
    }
  };
  frame.addEventListener("load", () => {
    if (activity !== op) return;
    const js = Uint8Array.from(atob(javascript), (byte) => byte.charCodeAt(0));
    const module = Uint8Array.from(atob(wasm), (byte) => byte.charCodeAt(0));
    frame.contentWindow!.postMessage({ javascript: js, wasm: module, stdin: input }, "*", [
      port2, js.buffer, module.buffer,
    ]);
  }, { once: true });
  frame.src = "/runner.html";
  document.body.append(frame);
}

async function build(run: boolean) {
  if (activity) return;
  const op = { request: new AbortController() };
  const source = JSON.stringify({ files: draft.files, entry: draft.entry, units: draft.units });
  const input = stdin.value;
  setActivity(op);
  clearResult();
  status.textContent = "Building…";
  try {
    let reply = run && cached?.source === source ? cached.reply : undefined;
    if (!reply) {
      const response = await fetch("/api/v1/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: source,
        signal: op.request.signal,
      });
      reply = await response.json() as Build;
      if (activity !== op) return;
      showDiagnostics(reply.diagnostics);
      if (!response.ok || !reply.javascript || !reply.wasm) {
        status.textContent = "Build failed";
        setActivity(null);
        return;
      }
      cached = { source, reply };
    } else {
      showDiagnostics(reply.diagnostics);
    }
    if (run && reply.javascript && reply.wasm) {
      status.textContent = "Running…";
      startRunner(op, reply.javascript, reply.wasm, input);
    } else {
      status.textContent = "Build succeeded";
      setActivity(null);
    }
  } catch {
    if (activity !== op) return;
    status.textContent = "Could not complete the build";
    setActivity(null);
  }
}

function applyTheme(light: boolean) {
  document.documentElement.dataset.theme = light ? "light" : "dark";
  theme.setAttribute("aria-pressed", String(light));
  theme.textContent = light ? "Dark theme" : "Light theme";
}

editor.addEventListener("input", () => {
  current().source = editor.value;
  numberLines();
  save();
});
editor.addEventListener("scroll", () => { lines.scrollTop = editor.scrollTop; });
stdin.addEventListener("input", () => { draft.stdin = stdin.value; save(); });
filename.addEventListener("change", rename);
filename.addEventListener("keydown", (event) => {
  if (event.key === "Enter") filename.blur();
});
entrySelect.addEventListener("change", () => {
  draft.entry = entrySelect.value;
  draft.units = draft.units.filter((path) => path !== draft.entry);
  render();
  save();
});
unit.addEventListener("change", () => {
  if (unit.checked) draft.units.push(draft.active);
  else draft.units = draft.units.filter((path) => path !== draft.active);
  save();
});
remove.addEventListener("click", () => {
  if (!confirm(`Remove ${draft.active} from this project?`)) return;
  draft.files = draft.files.filter((file) => file.path !== draft.active);
  draft.units = draft.units.filter((path) => path !== draft.active);
  views.delete(draft.active);
  if (draft.entry === draft.active) {
    draft.entry = draft.files[0].path;
    draft.units = draft.units.filter((path) => path !== draft.entry);
  }
  draft.active = draft.files[0].path;
  render();
  save();
});
examples.addEventListener("change", () => {
  const key = examples.value as keyof typeof exampleFiles;
  examples.value = "";
  if (key in exampleFiles && confirm("Replace the current draft with this example?")) {
    void loadExample(key);
  }
});
theme.addEventListener("click", () => {
  const light = document.documentElement.dataset.theme !== "light";
  applyTheme(light);
  putStorage(themeKey, light ? "light" : "dark");
});
buildButton.addEventListener("click", () => void build(false));
runButton.addEventListener("click", () => void build(true));
stopButton.addEventListener("click", () => {
  if (!activity) return;
  activity.request.abort();
  activity.stopRunner?.();
  setActivity(null);
  status.textContent = "Stopped";
});
document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    void build(true);
  }
});

applyTheme(getStorage(themeKey) === "light");
stdin.value = draft.stdin;
render();
if (!saved) void loadExample("hello");
