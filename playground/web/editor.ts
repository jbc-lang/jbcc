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
type SourceLocation = {
  path: string;
  source: string;
  line: number;
  column?: number;
  severity: string;
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
const sourceMark = element("source-mark");
const errorLine = element("error-line");
const errorColumn = element("error-column");
const sourceMeasure = element("source-measure");
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
const runButton = element<HTMLButtonElement>("run");
const stopButton = element<HTMLButtonElement>("stop");

const onlineAuth = fetch("/api/v1/auth/config").then(async (response) => {
  if (!response.ok) throw new Error("Could not load sign-in configuration");
  const config = await response.json();
  if (config === null) return null;
  const { connectAuth } = await import("./auth");
  const auth = connectAuth(config);
  element("cloud-projects").hidden = false;
  return auth;
});
void onlineAuth.catch(() => {
  element("auth-status").textContent = "Could not load sign-in";
});

const draftKey = "jbcc.playground.draft";
const themeKey = "jbcc.playground.theme";
const exampleFiles = {
  hello: ["hello.b"],
  fibonacci: ["fibonacci.b"],
  factorial: ["factorial.b"],
  rule110: ["rule110.b"],
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
let marked: SourceLocation | undefined;
let cached: { source: string; reply: Build & { javascript: string; wasm: string } } | undefined;
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
  syncEditorScroll();
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
  renderSourceMark();
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

function syncEditorScroll() {
  lines.scrollTop = editor.scrollTop;
  sourceMark.style.setProperty("--scroll-top", `${editor.scrollTop}px`);
  sourceMark.style.setProperty("--scroll-left", `${editor.scrollLeft}px`);
}

function measureSource(text: string): number {
  sourceMeasure.textContent = text;
  return sourceMeasure.getBoundingClientRect().width;
}

function renderSourceMark(reveal = false, focus = false) {
  const file = current();
  const location = marked?.path === file.path && marked.source === file.source ? marked : undefined;
  sourceMark.hidden = true;
  editor.removeAttribute("aria-invalid");
  if (!location) return;

  const sourceLines = editor.value.split("\n");
  const line = sourceLines[location.line - 1];
  if (line === undefined) return;
  const style = getComputedStyle(editor);
  const height = parseFloat(style.lineHeight);
  const top = parseFloat(style.paddingTop) + (location.line - 1) * height;
  const chars = Array.from(line);
  const index = Math.min((location.column ?? 1) - 1, chars.length);
  const prefix = chars.slice(0, index).join("");
  const prefixWidth = measureSource(prefix);
  const left = parseFloat(style.paddingLeft) + prefixWidth;
  const width = Math.max(2, measureSource(prefix + (chars[index] ?? "")) - prefixWidth);
  sourceMeasure.textContent = "";

  if (reveal) {
    const offset = sourceLines.slice(0, location.line - 1)
      .reduce((sum, previous) => sum + previous.length + 1, prefix.length);
    if (focus) editor.focus({ preventScroll: true });
    editor.setSelectionRange(offset, offset);
    if (top < editor.scrollTop || top + height > editor.scrollTop + editor.clientHeight) {
      editor.scrollTop = Math.max(0, top - height * 2);
    }
    if (left < editor.scrollLeft || left + width > editor.scrollLeft + editor.clientWidth) {
      editor.scrollLeft = Math.max(0, left - editor.clientWidth / 3);
    }
  }

  sourceMark.style.width = `${editor.clientWidth}px`;
  sourceMark.style.height = `${editor.clientHeight}px`;
  errorLine.style.top = `calc(${top}px - var(--scroll-top))`;
  errorLine.style.height = `${height}px`;
  errorColumn.hidden = location.column === undefined;
  errorColumn.style.left = `calc(${left}px - var(--scroll-left))`;
  errorColumn.style.width = `${width}px`;
  sourceMark.dataset.severity = location.severity;
  sourceMark.hidden = false;
  if (location.severity === "error") editor.setAttribute("aria-invalid", "true");
  syncEditorScroll();
}

function revealDiagnostic(location: SourceLocation, focus: boolean) {
  if (!draft.files.some((file) => file.path === location.path && file.source === location.source)) return;
  marked = location;
  if (draft.active !== location.path) switchTab(location.path);
  renderSourceMark(true, focus);
}

function showDiagnostics(items: Diagnostic[], sources?: Map<string, string>) {
  marked = undefined;
  renderSourceMark();
  box.replaceChildren();
  box.hidden = items.length === 0;
  let firstError: SourceLocation | undefined;
  for (const item of items) {
    const row = document.createElement("p");
    row.dataset.severity = item.severity;
    const { path, line, column } = item;
    const source = path ? sources?.get(path) : undefined;
    if (path && line && source !== undefined) {
      const location = { path, source, line, column, severity: item.severity };
      row.append(button(`${path}:${line}${column ? `:${column}` : ""}`, () => {
        revealDiagnostic(location, true);
      }), " ");
      if (item.severity === "error" && !firstError) firstError = location;
    }
    row.append(item.message);
    box.append(row);
  }
  if (firstError) revealDiagnostic(firstError, false);
}

function setActivity(value: Activity | null) {
  activity = value;
  runButton.disabled = examples.disabled = value !== null;
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

function isActive(op: Activity): boolean {
  return activity === op;
}

async function runProgram() {
  if (activity) return;
  const op = { request: new AbortController() };
  const source = JSON.stringify({ files: draft.files, entry: draft.entry, units: draft.units });
  const sources = new Map(draft.files.map((file) => [file.path, file.source]));
  const input = stdin.value;
  setActivity(op);
  clearResult();
  status.textContent = "Building…";
  try {
    const session = await onlineAuth;
    const identity = await session?.session();
    if (!isActive(op)) return;
    let reply = cached?.source === source && !session ? cached.reply : undefined;
    if (!reply) {
      const response = await fetch("/api/v1/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...identity?.headers },
        body: source,
        signal: op.request.signal,
      });
      const result = await response.json() as Build;
      if (!isActive(op)) return;
      showDiagnostics(result.diagnostics, sources);
      const { javascript, wasm } = result;
      if (!response.ok || !javascript || !wasm) {
        status.textContent = "Build failed";
        setActivity(null);
        return;
      }
      reply = { ...result, javascript, wasm };
      cached = { source, reply };
    } else {
      showDiagnostics(reply.diagnostics, sources);
    }
    status.textContent = "Running…";
    startRunner(op, reply.javascript, reply.wasm, input);
  } catch (error) {
    if (!isActive(op)) return;
    status.textContent = error instanceof Error && error.message === "Sign in with GitHub first"
      ? error.message
      : "Could not complete the build";
    setActivity(null);
  }
}

const revisions = new Map<string, number>();
const cloudName = element<HTMLInputElement>("cloud-project");
const cloudStatus = element("cloud-status");
const cloudSave = element<HTMLButtonElement>("cloud-save");
const cloudLoad = element<HTMLButtonElement>("cloud-load");

async function cloudProject(write: boolean) {
  const id = cloudName.value.trim();
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(id)) {
    cloudStatus.textContent = "Use letters, digits, hyphens or underscores";
    return;
  }
  if (!write && !confirm("Replace this local draft with the saved project?")) return;

  cloudSave.disabled = cloudLoad.disabled = true;
  cloudStatus.textContent = write ? "Saving…" : "Loading…";
  const before = JSON.stringify(draft);
  const { files, entry, units } = JSON.parse(before) as Draft;
  try {
    const auth = await onlineAuth;
    if (!auth) return;
    const identity = await auth.session();
    const key = JSON.stringify([identity.uid, id]);
    const revision = revisions.get(key) ?? 0;
    const response = await fetch(`/api/v1/projects/${encodeURIComponent(id)}`, write ? {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...identity.headers },
      body: JSON.stringify({ project: { files, entry, units }, revision }),
    } : { headers: identity.headers });
    const result = await response.json();
    if (!response.ok) throw new Error(result.diagnostics?.[0]?.message ?? "Could not access the cloud project");
    if ((await auth.session()).uid !== identity.uid) throw new Error("The signed-in account changed");
    if (!write) {
      if (activity || JSON.stringify(draft) !== before) {
        throw new Error("Draft kept because it changed while loading");
      }
      const project = result.project as Project;
      draft = { ...project, active: project.entry, stdin: draft.stdin };
      views.clear();
      clearResult();
      render();
      save();
      status.textContent = "Ready";
    }
    revisions.set(key, result.revision);
    cloudStatus.textContent = write ? "Saved" : "Loaded";
  } catch (error) {
    cloudStatus.textContent = error instanceof Error ? error.message : "Could not access the cloud project";
  } finally {
    cloudSave.disabled = cloudLoad.disabled = false;
  }
}

cloudSave.addEventListener("click", () => void cloudProject(true));
cloudLoad.addEventListener("click", () => void cloudProject(false));

function applyTheme(light: boolean) {
  document.documentElement.dataset.theme = light ? "light" : "dark";
  const label = light ? "Switch to dark theme" : "Switch to light theme";
  theme.setAttribute("aria-label", label);
  theme.title = label;
  theme.textContent = light ? "☾" : "☀︎";
}

editor.addEventListener("input", () => {
  current().source = editor.value;
  numberLines();
  renderSourceMark();
  save();
});
editor.addEventListener("scroll", syncEditorScroll);
new ResizeObserver(() => renderSourceMark()).observe(editor);
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
runButton.addEventListener("click", () => void runProgram());
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
    void runProgram();
  }
});

applyTheme(getStorage(themeKey) === "light");
stdin.value = draft.stdin;
render();
if (!saved) void loadExample("hello");
