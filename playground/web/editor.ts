import { compileInBrowser, type Diagnostic } from "./browser-compiler";
import {
  exportProject, importProject, listProjects, projectName, readProject, writeProject,
  type Draft, type SourceFile,
} from "./projects";

type ProjectBinding = { name: string; revision: number; savedVersion: number; failed?: boolean };
type StoredDraft = Draft & { localProject?: { name: string; revision: number; dirty: boolean } };
type SourceLocation = {
  path: string;
  source: string;
  line: number;
  column?: number;
  severity: string;
};
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
const helpButton = element<HTMLButtonElement>("help");
const helpDialog = element<HTMLDialogElement>("help-dialog");

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
    return true;
  } catch {
    return false;
  }
}

function loadDraft(): StoredDraft | null {
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
const { localProject: storedProject, ...storedDraft }: StoredDraft = saved ?? {
  files: [{ path: "main.b", source: "" }],
  entry: "main.b",
  units: [],
  active: "main.b",
  stdin: "",
};
let draft: Draft = storedDraft;
let localProject: ProjectBinding | undefined = storedProject &&
    typeof storedProject.name === "string" && projectName.test(storedProject.name) &&
    Number.isSafeInteger(storedProject.revision) && storedProject.revision > 0
  ? { name: storedProject.name, revision: storedProject.revision, savedVersion: storedProject.dirty ? -1 : 0 }
  : undefined;
let draftVersion = 0;
let saveTimer: number | undefined;
let saveStarted: number | undefined;
let projectBusy = false;
let autosaves = Promise.resolve();
let activity: Activity | null = null;
let marked: SourceLocation | undefined;
const views = new Map<string, { start: number; end: number; top: number; left: number }>();

function current(): SourceFile {
  return draft.files.find((file) => file.path === draft.active)!;
}

function persistDraft() {
  const binding = localProject;
  const snapshot: StoredDraft = binding ? {
    ...draft,
    localProject: { name: binding.name, revision: binding.revision, dirty: binding.savedVersion !== draftVersion },
  } : draft;
  if (!putStorage(draftKey, JSON.stringify(snapshot))) {
    projectStatus.textContent = "Could not store the recovery draft";
  }
}

function flushDraft() {
  if (saveTimer === undefined) return;
  window.clearTimeout(saveTimer);
  saveTimer = undefined;
  saveStarted = undefined;
  persistDraft();
  const binding = localProject;
  if (!binding || projectBusy || binding.savedVersion === draftVersion) return;
  const version = draftVersion;
  const snapshot = structuredClone(draft);
  autosaves = autosaves.then(async () => {
    if (binding.failed || binding.savedVersion >= version) return;
    try {
      binding.revision = await writeProject(binding.name, snapshot, binding.revision);
      binding.savedVersion = version;
      if (localProject === binding) persistDraft();
    } catch (error) {
      binding.failed = true;
      if (localProject === binding) {
        localProject = undefined;
        persistDraft();
        projectStatus.textContent = error instanceof Error ? error.message : "Could not autosave the project";
      }
    }
  });
}

function scheduleSave() {
  window.clearTimeout(saveTimer);
  const now = performance.now();
  saveStarted ??= now;
  const delay = Math.max(0, Math.min(350, 2000 - (now - saveStarted)));
  saveTimer = window.setTimeout(flushDraft, delay);
}

function save() {
  draftVersion++;
  scheduleSave();
}

function replaceDraft(value: Draft, binding?: { name: string; revision: number }) {
  flushDraft();
  draft = value;
  draftVersion++;
  localProject = binding ? { ...binding, savedVersion: draftVersion } : undefined;
  views.clear();
  stdin.value = draft.stdin;
  clearResult();
  render();
  persistDraft();
  status.textContent = "Ready";
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
      const response = await fetch(`./examples/${path}`);
      if (!response.ok) throw new Error("Could not load example");
      return { path, source: await response.text() };
    }));
    if (activity || projectBusy || JSON.stringify(draft) !== before) {
      if (!activity) status.textContent = "Draft kept because it changed while loading";
      return;
    }
    replaceDraft({
      files,
      entry: files[0].path,
      active: files[0].path,
      units: key === "status" ? [files[1].path] : [],
      stdin: "",
    });
    projectNameField.value = "draft";
    projectStatus.textContent = "";
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

function startRunner(
  op: Activity,
  wasm: Uint8Array<ArrayBuffer>,
  input: string,
  runnerHTML: string,
) {
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
    frame.contentWindow!.postMessage({ wasm, stdin: input }, "*", [port2, wasm.buffer]);
  }, { once: true });
  frame.srcdoc = runnerHTML;
  document.body.append(frame);
}

let runnerDocument: string | undefined;

async function loadRunnerDocument(signal: AbortSignal) {
  if (runnerDocument !== undefined) return runnerDocument;
  const response = await fetch("./runner.html", { signal });
  if (!response.ok) throw new Error("Could not load the browser runner");
  runnerDocument = await response.text();
  return runnerDocument;
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
    const [result, runnerHTML] = await Promise.all([
      compileInBrowser(source, op.request.signal, (text) => {
        if (isActive(op)) status.textContent = text;
      }),
      loadRunnerDocument(op.request.signal),
    ]);
    if (!isActive(op)) return;
    showDiagnostics(result.diagnostics, sources);
    if (!result.wasm) {
      status.textContent = "Build failed";
      setActivity(null);
      return;
    }
    status.textContent = "Running…";
    startRunner(op, result.wasm, input, runnerHTML);
  } catch (error) {
    if (!isActive(op)) return;
    op.request.abort();
    status.textContent = error instanceof Error
      ? error.message
      : "Could not complete the build";
    setActivity(null);
  }
}

const projectNameField = element<HTMLInputElement>("project-name");
const projectStatus = element("project-status");
const projectSave = element<HTMLButtonElement>("project-save");
const projectLoad = element<HTMLButtonElement>("project-load");
const projectImport = element<HTMLButtonElement>("project-import");
const projectFile = element<HTMLInputElement>("project-file");
const projectPicker = element<HTMLDetailsElement>("project-picker");
const projectNames = element("project-names");
const projectListStatus = element("project-list-status");
// Ignore a list result if the picker was closed or reopened while reading.
let listVersion = 0;

function closeProjectList() {
  listVersion++;
  projectNames.replaceChildren();
  projectListStatus.textContent = "";
}

async function listSavedProjects() {
  const version = ++listVersion;
  projectListStatus.textContent = "Loading projects…";
  try {
    const names = await listProjects();
    if (!projectPicker.open || version !== listVersion) return;
    projectNames.replaceChildren(...names.map((name) => button(name, () => {
      projectNameField.value = name;
      projectPicker.open = false;
      projectNameField.focus();
    })));
    projectListStatus.textContent = names.length ? "" : "No saved projects";
  } catch (error) {
    if (version === listVersion) {
      projectListStatus.textContent = error instanceof Error ? error.message : "Could not list projects";
    }
  }
}

projectPicker.addEventListener("toggle", () => {
  if (projectPicker.open) void listSavedProjects();
  else closeProjectList();
});
projectPicker.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && projectPicker.open) {
    projectPicker.open = false;
    projectPicker.querySelector("summary")?.focus();
  }
});
document.addEventListener("pointerdown", (event) => {
  if (projectPicker.open && event.target instanceof Node && !projectPicker.contains(event.target)) {
    projectPicker.open = false;
  }
});
async function runLocalProject(action: () => Promise<void>) {
  if (projectBusy) return;
  flushDraft();
  projectBusy = true;
  projectSave.disabled = projectLoad.disabled = projectImport.disabled = true;
  try {
    await autosaves;
    await action();
  } catch (error) {
    projectStatus.textContent = error instanceof Error ? error.message : "Could not access browser projects";
  } finally {
    projectBusy = false;
    projectSave.disabled = projectLoad.disabled = projectImport.disabled = false;
    if (localProject && localProject.savedVersion !== draftVersion) scheduleSave();
  }
}

function manageLocalProject(write: boolean) {
  const name = projectNameField.value.trim();
  if (!projectName.test(name)) {
    projectStatus.textContent = "Use letters, digits, hyphens or underscores";
    return;
  }
  const before = draftVersion;
  void runLocalProject(async () => {
    const saved = await readProject(name);
    if (write) {
      if (saved && saved.revision !== (localProject?.name === name ? localProject.revision : 0) &&
          !confirm(`Replace the saved project “${name}” with this draft?`)) return;
      const version = draftVersion;
      const revision = await writeProject(name, structuredClone(draft), saved?.revision ?? 0);
      localProject = { name, revision, savedVersion: version };
      projectStatus.textContent = `Autosaving ${name}`;
      persistDraft();
    } else {
      if (!saved) throw new Error("Project not found");
      if (activity || draftVersion !== before) throw new Error("Draft kept because it changed while loading");
      if (!confirm(`Replace this draft with “${name}”?`)) return;
      projectStatus.textContent = `Autosaving ${name}`;
      replaceDraft(saved.draft, { name, revision: saved.revision });
    }
    projectNameField.value = name;
  });
}

projectSave.addEventListener("click", () => manageLocalProject(true));
projectLoad.addEventListener("click", () => manageLocalProject(false));
element("project-export").addEventListener("click", () => {
  const name = localProject?.name ?? projectNameField.value.trim();
  if (!projectName.test(name)) {
    projectStatus.textContent = "Enter a project name before exporting";
    return;
  }
  try {
    exportProject(name, draft);
    projectStatus.textContent = `Exported ${name}`;
  } catch (error) {
    projectStatus.textContent = error instanceof Error ? error.message : "Could not export the project";
  }
});
projectImport.addEventListener("click", () => projectFile.click());
projectFile.addEventListener("change", () => {
  const file = projectFile.files?.[0];
  projectFile.value = "";
  if (!file) return;
  const before = draftVersion;
  void runLocalProject(async () => {
    const imported = await importProject(file);
    const { name } = imported;
    const saved = await readProject(name);
    if (activity || before !== draftVersion) throw new Error("Draft kept because it changed while importing");
    if (!confirm(saved
      ? `Overwrite “${name}” and replace the current draft with this import?`
      : `Save “${name}” and replace the current draft with this import?`)) return;
    const revision = await writeProject(name, imported.draft, saved?.revision ?? 0);
    if (activity || before !== draftVersion) {
      throw new Error(`Imported ${name}. The current draft changed and was kept`);
    }
    projectStatus.textContent = `Autosaving ${name}`;
    replaceDraft(imported.draft, { name, revision });
    projectNameField.value = name;
  });
});

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
window.addEventListener("pagehide", flushDraft);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") flushDraft();
});
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
helpButton.addEventListener("click", () => helpDialog.showModal());
helpDialog.addEventListener("close", () => helpButton.focus());
stopButton.addEventListener("click", () => {
  if (!activity) return;
  activity.request.abort();
  activity.stopRunner?.();
  setActivity(null);
  status.textContent = "Stopped";
});
document.addEventListener("keydown", (event) => {
  if (!helpDialog.open && (event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    void runProgram();
  }
});

applyTheme(getStorage(themeKey) === "light");
stdin.value = draft.stdin;
render();
if (localProject) {
  projectNameField.value = localProject.name;
  projectStatus.textContent = `Autosaving ${localProject.name}`;
  if (localProject.savedVersion !== draftVersion) scheduleSave();
}
if (!saved) void loadExample("hello");
