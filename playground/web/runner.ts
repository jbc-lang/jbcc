type RunRequest = {
  javascript?: Uint8Array<ArrayBuffer>;
  wasm: Uint8Array<ArrayBuffer>;
  stdin: string;
};
type RunEvent =
  | { type: "stdout" | "stderr"; text: string }
  | { type: "exit"; status: number }
  | { type: "error"; message: string };

declare const createProgram: (options: {
  wasmBinary: Uint8Array;
  stdin: () => number | null;
  stdout: (byte: number | null) => void;
  stderr: (byte: number | null) => void;
  onExit: (code: number) => void;
}) => Promise<unknown>;
declare const wasiWorkerSource: string;

// This function is serialized into the dedicated worker alongside the loader.
function workerMain() {
  self.onmessage = async ({ data }: MessageEvent<RunRequest>) => {
    const stdin = new TextEncoder().encode(data.stdin);
    let position = 0;
    let bytesLeft = 64 * 1024;
    let overflow = false;
    let status = 0;
    const streams = {
      stdout: { bytes: [] as number[], decoder: new TextDecoder() },
      stderr: { bytes: [] as number[], decoder: new TextDecoder() },
    };

    function flush(type: "stdout" | "stderr", final = false) {
      const stream = streams[type];
      const text = stream.decoder.decode(Uint8Array.from(stream.bytes), { stream: !final });
      stream.bytes.length = 0;
      if (text) self.postMessage({ type, text } satisfies RunEvent);
    }

    function write(type: "stdout" | "stderr", byte: number | null) {
      if (overflow) return;
      if (byte === null) {
        flush(type);
        return;
      }
      if (bytesLeft-- === 0) {
        flush("stdout", true);
        flush("stderr", true);
        overflow = true;
        self.postMessage({ type: "error", message: "Program output exceeded 64 KiB" } satisfies RunEvent);
        return;
      }
      const buffer = streams[type].bytes;
      buffer.push(byte);
      if (byte === 10 || buffer.length >= 4096) flush(type);
    }

    try {
      await createProgram({
        wasmBinary: data.wasm,
        stdin: () => stdin[position++] ?? null,
        stdout: (byte) => write("stdout", byte),
        stderr: (byte) => write("stderr", byte),
        onExit: (code) => { status = code; },
      });
      flush("stdout", true);
      flush("stderr", true);
      if (!overflow) self.postMessage({ type: "exit", status } satisfies RunEvent);
    } catch (error) {
      flush("stdout", true);
      flush("stderr", true);
      if (!overflow) self.postMessage({ type: "error", message: String(error) } satisfies RunEvent);
    }
  };
}

function connect(event: MessageEvent<RunRequest>) {
  // Static serving also exposes runner.html as a standalone document.
  if (
    window.origin !== "null" ||
    event.source !== parent ||
    event.origin !== new URL(document.baseURI).origin ||
    event.ports.length !== 1
  ) return;
  window.removeEventListener("message", connect);
  const port = event.ports[0];
  let worker: Worker;
  let timer: number;
  let url: string;
  function finish(message?: RunEvent) {
    if (message) port.postMessage(message);
    worker?.terminate();
    window.clearTimeout(timer);
    if (url) URL.revokeObjectURL(url);
    port.close();
  }
  try {
    const { javascript, wasm, stdin } = event.data;
    const scripts = javascript
      ? [javascript, "\n;", `(${workerMain.toString()})();`]
      : [wasiWorkerSource];
    url = URL.createObjectURL(new Blob(scripts, { type: "text/javascript" }));
    worker = new Worker(url);
    worker.onmessage = ({ data }: MessageEvent<RunEvent>) => {
      if (data.type === "exit" || data.type === "error") finish(data);
      else port.postMessage(data);
    };
    worker.onerror = () => finish({ type: "error", message: "Unable to start the Wasm worker" });
    port.onmessage = () => finish();
    timer = window.setTimeout(() => finish({ type: "error", message: "Run exceeded 5 seconds" }), 5000);
    worker.postMessage({ wasm, stdin }, [wasm.buffer]);
  } catch {
    finish({ type: "error", message: "Unable to start the Wasm worker" });
  }
}

window.addEventListener("message", connect);
