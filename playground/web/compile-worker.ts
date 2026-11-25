import type { CompilerMessage, Diagnostic } from "./browser-compiler";

declare const PYODIDE_ASSET: string;
declare const CLANG_ASSET: string;

type Python = {
  FS: { mkdirTree(path: string): void; writeFile(path: string, contents: Uint8Array): void };
  globals: { set(name: string, value: string): void; delete(name: string): void };
  runPython(code: string): string;
};

type Clang = {
  commands: {
    clang(
      args: string[],
      files: Record<string, string>,
      options: { stderr: (bytes: Uint8Array | null) => void; decodeASCII: false },
    ): Promise<Record<string, Uint8Array<ArrayBuffer>>>;
  };
};

let python: Python | undefined;
let clang: Clang | undefined;

function progress(status: string) {
  self.postMessage({ status } satisfies CompilerMessage);
}

async function loadPython() {
  progress("Loading Python…");
  const url = new URL(PYODIDE_ASSET, import.meta.url).href;
  const { loadPyodide } = await import(url) as { loadPyodide(): Promise<Python> };
  const py = await loadPyodide();
  py.FS.mkdirTree("/opt/jbcc");
  const files = ["browser.py", "translate.py", "jbcc/__init__.py", "jbcc/compiler.py", "jbcc/jbc.c"];
  await Promise.all(files.map(async (file) => {
    const response = await fetch(new URL(`./python/${file}`, import.meta.url));
    if (!response.ok) throw new Error(`Could not load ${file}`);
    py.FS.writeFile(`/opt/${file}`, new Uint8Array(await response.arrayBuffer()));
  }));
  py.runPython("import sys; sys.path.insert(0, '/opt'); from browser import compile_project");
  return py;
}

function diagnostics(text: string): Diagnostic[] {
  return text.trim().split("\n").filter(Boolean).map((line) => {
    const match = /^(.*?):(\d+):(\d+):\s*(.*)$/.exec(line);
    const message = match?.[4] ?? line;
    const warning = message.startsWith("warning: ");
    return {
      ...(match && { path: match[1], line: Number(match[2]), column: Number(match[3]) }),
      severity: warning ? "warning" : "error",
      message: warning ? message.slice(9) : message,
    };
  });
}

self.onmessage = async ({ data }: MessageEvent<string>) => {
  const messages: Diagnostic[] = [];
  let clangOutput = "";
  try {
    python ??= await loadPython();
    progress("Translating jBC…");
    python.globals.set("project_json", data);
    const result = JSON.parse(python.runPython("compile_project(project_json)")) as {
      source: string | null;
      diagnostics: string;
    };
    python.globals.delete("project_json");
    messages.push(...diagnostics(result.diagnostics));
    if (result.source !== null) {
      if (!clang) {
        progress("Loading the C compiler…");
        const url = new URL(CLANG_ASSET, import.meta.url).href;
        clang = await import(url) as Clang;
      }
      progress("Compiling C…");
      const decoder = new TextDecoder();
      const output = await clang.commands.clang(
        ["-std=c99", "-O0", "program.c", "-lm", "-lc-printscan-long-double",
          "-Wl,--max-memory=67108864", "-o", "program.wasm"],
        { "program.c": result.source },
        {
          decodeASCII: false,
          stderr: (bytes) => { clangOutput += decoder.decode(bytes ?? undefined, { stream: !!bytes }); },
        },
      );
      const wasm = output["program.wasm"];
      if (!wasm || wasm.byteLength > 4 * 1024 * 1024) {
        throw new Error("Missing or oversized WebAssembly output");
      }
      self.postMessage({ diagnostics: messages, wasm } satisfies CompilerMessage, { transfer: [wasm.buffer] });
      return;
    }
  } catch (error) {
    messages.push({ severity: "error", message: clangOutput.trim() || String(error) });
  }
  self.postMessage({ diagnostics: messages } satisfies CompilerMessage);
};
