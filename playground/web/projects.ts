export type SourceFile = { path: string; source: string };
export type Project = { files: SourceFile[]; entry: string; units: string[] };
export type Draft = Project & { active: string; stdin: string };

export const projectName = /^[A-Za-z0-9_-]{1,64}$/;
const maxExportSize = 8 * 1024 * 1024;
const pathPart = /^[A-Za-z0-9_.-]+$/;

type NamedProject = { name: string; draft: Draft; revision: number };

let openDatabase: Promise<IDBDatabase> | undefined;

function database() {
  return openDatabase ??= new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open("jbcc.playground", 1);
    request.onupgradeneeded = () => request.result.createObjectStore("projects", { keyPath: "name" });
    request.onsuccess = () => {
      const db = request.result;
      db.onversionchange = () => {
        db.close();
        openDatabase = undefined;
      };
      resolve(db);
    };
    request.onerror = () => reject(request.error);
  }).catch((error) => {
    openDatabase = undefined;
    throw error;
  });
}

function result<T>(request: IDBRequest<T>) {
  return new Promise<T>((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function listProjects() {
  const db = await database();
  return result(db.transaction("projects").objectStore("projects").getAllKeys()) as Promise<string[]>;
}

export async function readProject(name: string) {
  const db = await database();
  return result(db.transaction("projects").objectStore("projects").get(name)) as Promise<NamedProject | undefined>;
}

export async function writeProject(name: string, draft: Draft, previous: number) {
  const db = await database();
  return new Promise<number>((resolve, reject) => {
    const transaction = db.transaction("projects", "readwrite");
    const projects = transaction.objectStore("projects");
    const read = projects.get(name);
    let revision = previous + 1;
    read.onsuccess = () => {
      const current = read.result as NamedProject | undefined;
      if ((current?.revision ?? 0) === previous) {
        projects.put({ name, draft, revision } satisfies NamedProject);
      } else {
        // A page may close after IndexedDB committed the recovery draft.
        revision = current && JSON.stringify(current.draft) === JSON.stringify(draft) ? current.revision : 0;
      }
    };
    transaction.oncomplete = () => {
      if (revision) resolve(revision);
      else reject(new Error("Project changed in another tab. Your draft was kept"));
    };
    transaction.onabort = () => reject(transaction.error ?? new Error("Project save was interrupted"));
  });
}

export function exportProject(name: string, draft: Draft) {
  const { files, entry, units, active, stdin } = draft;
  const file = new Blob([JSON.stringify({ version: 1, name, files, entry, units, active, stdin }, null, 2) + "\n"], {
    type: "application/json",
  });
  if (file.size > maxExportSize) throw new Error("Project file exceeds 8 MiB");
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.download = `${name}.jbc-project.json`;
  link.href = url;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function validPath(path: unknown): path is string {
  return typeof path === "string" && path.length <= 240 && !path.startsWith("-") &&
    path.split("/").every((part) => part !== "." && part !== ".." && pathPart.test(part));
}

export async function importProject(file: File): Promise<{ name: string; draft: Draft }> {
  if (file.size > maxExportSize) throw new Error("Project file exceeds 8 MiB");
  let value: unknown;
  try {
    value = JSON.parse(await file.text());
  } catch {
    throw new Error("Project file must be valid JSON");
  }
  if (!object(value) || value.version !== 1) throw new Error("Unsupported project file version");
  const { name, files, entry, units, active, stdin } = value;
  if (typeof name !== "string" || !projectName.test(name) || !Array.isArray(files) ||
      !Array.isArray(units) || (stdin !== undefined && typeof stdin !== "string")) {
    throw new Error("Invalid project file");
  }
  const projectFiles: SourceFile[] = [];
  const paths = new Set<string>();
  for (const file of files) {
    if (!object(file) || !validPath(file.path) || typeof file.source !== "string" || paths.has(file.path)) {
      throw new Error("Invalid or duplicate source file path");
    }
    paths.add(file.path);
    projectFiles.push({ path: file.path, source: file.source });
  }
  for (const path of paths) {
    for (let index = path.indexOf("/"); index !== -1; index = path.indexOf("/", index + 1)) {
      if (paths.has(path.slice(0, index))) throw new Error("File path conflicts with a project directory");
    }
  }
  if (typeof entry !== "string" || !paths.has(entry) ||
      new Set(units).size !== units.length ||
      !units.every((unit) => typeof unit === "string" && unit !== entry && paths.has(unit)) ||
      (active !== undefined && (typeof active !== "string" || !paths.has(active)))) {
    throw new Error("Invalid main file, linked routines, or selected tab");
  }
  return {
    name,
    draft: { files: projectFiles, entry, units, active: active ?? entry, stdin: stdin ?? "" },
  };
}
