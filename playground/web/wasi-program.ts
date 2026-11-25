import { ConsoleStdout, File, OpenFile, WASI } from "@bjorn3/browser_wasi_shim";

const outputLimit = Symbol("output limit");
const permittedImports = [
  "args_get", "args_sizes_get", "environ_get", "environ_sizes_get",
  "clock_time_get", "clock_res_get", "random_get", "proc_exit", "sched_yield",
  "fd_read", "fd_write", "fd_seek", "fd_close", "fd_fdstat_get", "fd_filestat_get",
  "fd_prestat_get", "fd_prestat_dir_name",
];

self.onmessage = async ({ data }: MessageEvent<{ wasm: Uint8Array<ArrayBuffer>; stdin: string }>) => {
  let remaining = 64 * 1024;
  const streams = {
    stdout: new TextDecoder(),
    stderr: new TextDecoder(),
  };
  function emit(type: keyof typeof streams, bytes?: Uint8Array) {
    const text = streams[type].decode(bytes, { stream: bytes !== undefined });
    if (text) self.postMessage({ type, text });
  }
  function sink(type: keyof typeof streams) {
    return new ConsoleStdout((bytes) => {
      emit(type, bytes.subarray(0, remaining));
      remaining -= bytes.length;
      if (remaining < 0) throw outputLimit;
    });
  }
  const wasi = new WASI(["program"], [], [
    new OpenFile(new File(new TextEncoder().encode(data.stdin), { readonly: true })),
    sink("stdout"),
    sink("stderr"),
  ]);
  try {
    const imports = Object.fromEntries(permittedImports.map((name) => [name, wasi.wasiImport[name]]));
    const { instance } = await WebAssembly.instantiate(data.wasm, { wasi_snapshot_preview1: imports });
    const status = wasi.start(instance as Parameters<WASI["start"]>[0]);
    emit("stdout");
    emit("stderr");
    self.postMessage({ type: "exit", status });
  } catch (error) {
    emit("stdout");
    emit("stderr");
    self.postMessage({
      type: "error",
      message: error === outputLimit ? "Program output exceeded 64 KiB" : String(error),
    });
  }
};
