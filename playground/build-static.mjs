import { createHash } from "node:crypto";
import { copyFile, cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";

process.chdir(import.meta.dir);
const output = "../dist/playground";
const { devDependencies } = await Bun.file("package.json").json();
const pyodide = `toolchain/pyodide-${devDependencies.pyodide}`;
const clang = `toolchain/clang-${devDependencies["@yowasp/clang"]}`;
const analytics = process.env.JBCC_ANALYTICS_FRAME && new URL(process.env.JBCC_ANALYTICS_FRAME);
if (analytics && (analytics.protocol !== "https:" || analytics.username || analytics.password || analytics.search || analytics.hash)) {
  throw new Error("JBCC_ANALYTICS_FRAME must be an HTTPS URL without credentials, query, or fragment");
}

async function bundle(options) {
  const result = await Bun.build({ target: "browser", ...options });
  if (!result.success) {
    throw new Error(result.logs.map((log) => log.message).join("\n"));
  }
  return result.outputs;
}

async function copy(source, destination) {
  await copyFile(source, join(output, destination));
}

function scriptHash(source) {
  return createHash("sha256").update(source).digest("base64");
}

await rm(output, { recursive: true, force: true });
await Promise.all(["examples", "python/jbcc", pyodide].map((path) =>
  mkdir(join(output, path), { recursive: true })));
await Promise.all([
  bundle({
    entrypoints: analytics ? ["web/editor.ts", "web/analytics.ts"] : ["web/editor.ts"],
    outdir: output,
    splitting: true,
  }),
  bundle({
    entrypoints: ["web/compile-worker.ts"],
    outdir: output,
    define: {
      PYODIDE_ASSET: JSON.stringify(`./${pyodide}/pyodide.mjs`),
      CLANG_ASSET: JSON.stringify(`./${clang}/bundle.js`),
    },
  }),
  ...["favicon-32.png", "style.css"].map((file) => copy(`web/${file}`, file)),
  ...["hello.b", "fibonacci.b", "factorial.b", "rule110.b"].map((file) =>
    copy(`../tests/programs/${file}`, `examples/${file}`)),
  ...["caller.b", "get.status.b", "I_STATUS"].map((file) =>
    copy(`../tests/routines/${file}`, `examples/${file}`)),
  copy("browser.py", "python/browser.py"),
  ...["__init__.py", "compiler.py", "jbc.c"].map((file) =>
    copy(`../src/jbcc/${file}`, `python/jbcc/${file}`)),
  ...["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "pyodide-lock.json", "python_stdlib.zip"]
    .map((file) => copy(`node_modules/pyodide/${file}`, `${pyodide}/${file}`)),
  cp("node_modules/@yowasp/clang/gen", join(output, clang), { recursive: true }),
  copy("../LICENSE", "LICENSE"),
  copy("../THIRD-PARTY-NOTICES.md", "THIRD-PARTY-NOTICES.md"),
  copy("TOOLCHAIN-NOTICES.md", "TOOLCHAIN-NOTICES.md"),
  copy("node_modules/@bjorn3/browser_wasi_shim/LICENSE-MIT", "WASI-SHIM-LICENSE"),
]);

const html = await readFile("web/index.html", "utf8");
const stamp = new Date().toISOString().slice(0, 16);
const analyticsScript = '    <script type="module" src="./analytics.js"></script>\n';
const page = analytics
  ? html.replace('data-compiler="browser"', `data-compiler="browser" data-analytics-frame="${analytics.href}"`)
  : html.replace(analyticsScript, "");
await writeFile(join(output, "index.html"), page
  .replace("__BUILD_TIME_ISO__", `${stamp}:00Z`)
  .replace("__BUILD_TIME_LABEL__", stamp.replaceAll("-", ".").replace("T", " ")));

const [[frame], [program]] = await Promise.all([
  bundle({ entrypoints: ["web/runner.ts"], format: "iife" }),
  bundle({ entrypoints: ["web/wasi-program.ts"], format: "iife" }),
]);
const script = (`const wasiWorkerSource = ${JSON.stringify(await program.text())};\n` +
  await frame.text()).replace(/<\/script/gi, "<\\/script");
const runner = await readFile("web/runner.html", "utf8");
const policy = `default-src 'none'; script-src 'sha256-${scriptHash(script)}' 'wasm-unsafe-eval'; worker-src blob:; base-uri 'none'; form-action 'none'`;
await writeFile(join(output, "runner.html"), runner.replace(
  '  <script src="./runner.js"></script>',
  `  <meta http-equiv="Content-Security-Policy" content="${policy}">\n  <script>${script}</script>`,
));
if (analytics) {
  const tagCheck = await readFile("analytics/tag-check.html", "utf8");
  const initializer = tagCheck.match(/<script>([\s\S]+?)<\/script>/)?.[1];
  if (!initializer) throw new Error("Could not find the Google tag initializer");
  const tagPolicy = `default-src 'none'; script-src 'sha256-${scriptHash(initializer)}' https://www.googletagmanager.com; base-uri 'none'; form-action 'none'`;
  await writeFile(join(output, "tag-check.html"), tagCheck.replace(
    "    <title>", `    <meta http-equiv="Content-Security-Policy" content="${tagPolicy}">\n    <title>`,
  ));
}
console.log(`Built ${output}`);
