type RunRequest = {
  wasm: Uint8Array<ArrayBuffer>;
  stdin: string;
};
type RunEvent =
  | { type: "stdout" | "stderr"; text: string }
  | { type: "exit"; status: number }
  | { type: "error"; message: string };

declare const wasiWorkerSource: string;

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
    const { wasm, stdin } = event.data;
    url = URL.createObjectURL(new Blob([wasiWorkerSource], { type: "text/javascript" }));
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
