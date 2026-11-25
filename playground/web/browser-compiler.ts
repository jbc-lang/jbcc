export type Diagnostic = {
  path?: string;
  line?: number;
  column?: number;
  severity: string;
  message: string;
};

export type CompilerMessage =
  | { status: string }
  | { diagnostics: Diagnostic[]; wasm?: Uint8Array<ArrayBuffer> };

let worker: Worker | undefined;

export function compileInBrowser(source: string, signal: AbortSignal, onStatus: (status: string) => void) {
  signal.throwIfAborted();
  const compiler = worker ??= new Worker("./compile-worker.js", { type: "module" });
  return new Promise<Extract<CompilerMessage, { diagnostics: Diagnostic[] }>>((resolve, reject) => {
    function finish(reset = false) {
      clearTimeout(timer);
      signal.removeEventListener("abort", abort);
      compiler.onmessage = null;
      compiler.onerror = null;
      if (reset) {
        compiler.terminate();
        worker = undefined;
      }
    }
    function abort() {
      finish(true);
      reject(signal.reason);
    }
    const timer = setTimeout(() => {
      finish(true);
      reject(new Error("Browser compilation timed out"));
    }, 120_000);
    signal.addEventListener("abort", abort, { once: true });
    compiler.onerror = () => {
      finish(true);
      reject(new Error("Could not start the browser compiler"));
    };
    compiler.onmessage = ({ data }: MessageEvent<CompilerMessage>) => {
      if ("status" in data) {
        onStatus(data.status);
      } else {
        finish();
        resolve(data);
      }
    };
    compiler.postMessage(source);
  });
}
