import { expect, test, type Page } from "@playwright/test";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const repo = fileURLToPath(new URL("../../", import.meta.url));
const fixture = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");

async function openEditor(page: Page) {
  await page.goto("/");
  await expect(page.locator("#filename")).toHaveValue("hello.b");
}

async function compareWithNative(page: Page, paths: string[], input = "") {
  const native = spawnSync("./jbcc", ["--run", ...paths], {
    cwd: repo, encoding: "utf8", input,
  });
  expect(native.error).toBeUndefined();
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(`Exited with status ${native.status}`, { timeout: 20000 });
  expect(await page.locator("#stdout").textContent()).toBe(native.stdout);
  expect(await page.locator("#stderr").textContent()).toBe(native.stderr);
}

test("builds and runs both examples, then reloads the multi-file draft", async ({ page }) => {
  await openEditor(page);
  await page.getByRole("button", { name: "Build", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Build succeeded", { timeout: 20000 });
  await compareWithNative(page, ["tests/programs/hello.b"]);

  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByLabel("Example").selectOption("status");
  await expect(page.locator("#filename")).toHaveValue("caller.b");
  await compareWithNative(page, ["tests/routines/caller.b", "tests/routines/get.status.b"]);
  await page.getByRole("button", { name: "get.status.b", exact: true }).click();
  await expect(page.getByLabel("Link as routine")).toBeChecked();
  await page.reload();
  await expect(page.locator("#filename")).toHaveValue("get.status.b");
  await expect(page.getByLabel("Main", { exact: true })).toHaveValue("caller.b");
});

test("passes prefilled stdin and preserves stderr and a nonzero exit status", async ({ page }) => {
  await openEditor(page);
  await page.getByLabel("jBC source").fill(fixture("fixtures/input.b"));
  await page.getByLabel("Standard input").fill("Wasm\n");
  await compareWithNative(page, ["playground/tests/fixtures/input.b"], "Wasm\n");
});

test("links unsupported operation errors back to their file and column", async ({ page }) => {
  await openEditor(page);
  await page.getByLabel("jBC source").fill(fixture("fixtures/unsupported.b"));
  await page.getByRole("button", { name: "Build", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Build failed");
  await expect(page.locator("#diagnostics")).toContainText("PERFORM is unavailable in the browser");
  await page.getByRole("button", { name: "hello.b:1:1" }).click();
  await expect(page.getByLabel("jBC source")).toBeFocused();
});

test("Stop terminates a running program and the next build succeeds", async ({ page }) => {
  await openEditor(page);
  await page.getByLabel("jBC source").fill(fixture("fixtures/loop.b"));
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Running…");
  await page.getByRole("button", { name: "Stop", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Stopped");
  await expect(page.locator("iframe")).toHaveCount(0);
  await page.getByLabel("jBC source").fill(fixture("../../tests/programs/hello.b"));
  await compareWithNative(page, ["tests/programs/hello.b"]);
});

test("terminates runs at the output and execution limits", async ({ page }) => {
  await openEditor(page);
  await page.getByLabel("jBC source").fill(fixture("fixtures/output-limit.b"));
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Program output exceeded 64 KiB", { timeout: 20000 });
  expect((await page.locator("#stdout").textContent())?.length).toBe(65536);

  await page.getByLabel("jBC source").fill(fixture("fixtures/loop.b"));
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Run exceeded 5 seconds", { timeout: 20000 });
  await expect(page.locator("iframe")).toHaveCount(0);
});

test("the iframe has an opaque origin and the runner cannot use editor storage or fetch", async ({ page }) => {
  await openEditor(page);
  const probe = fixture("fixtures/runner-probe.js");
  const result = await page.evaluate(async (source) => {
    localStorage.setItem("runner-probe", "editor");
    const frame = document.createElement("iframe");
    frame.sandbox.add("allow-scripts");
    frame.src = "/runner.html";
    const loaded = new Promise<void>((resolve) => frame.addEventListener("load", () => resolve(), { once: true }));
    document.body.append(frame);
    await loaded;
    const target = frame.contentWindow!;
    let inaccessible = false;
    try {
      void target.localStorage;
    } catch {
      inaccessible = true;
    }
    const channel = new MessageChannel();
    const result = await new Promise<string>((resolve) => {
      let output = "";
      channel.port1.onmessage = ({ data }) => {
        if (data.type === "stdout") output += data.text;
        if (data.type === "exit") resolve(output);
        if (data.type === "error") resolve(data.message);
      };
      const javascript = new TextEncoder().encode(
        source.replace("http://127.0.0.1:18765", window.location.origin),
      );
      target.postMessage({ javascript, wasm: new Uint8Array(), stdin: "" }, "*", [channel.port2]);
    });
    frame.remove();
    return { inaccessible, result };
  }, probe);
  expect(result).toEqual({ inaccessible: true, result: "storage=undefined; network=blocked\n" });
});
