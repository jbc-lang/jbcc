import { expect, test, type Page } from "@playwright/test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const repo = fileURLToPath(new URL("../../", import.meta.url));
const fixture = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");

async function openEditor(page: Page) {
  await page.goto("/");
  await expect(page.locator("#filename")).toHaveValue("hello.b");
}

async function compareWithNative(page: Page, paths: string[], input = "") {
  const directory = mkdtempSync(join(tmpdir(), "jbcc-playground-"));
  try {
    const executable = join(directory, "program");
    const build = spawnSync("./jbcc", ["--exe", "-o", executable, ...paths], { cwd: repo, encoding: "utf8" });
    expect(build.error).toBeUndefined();
    expect(build.status, build.stderr).toBe(0);
    const native = spawnSync(executable, [], { cwd: repo, encoding: "utf8", input });
    expect(native.error).toBeUndefined();
    await page.getByRole("button", { name: "Run", exact: true }).click();
    await expect(page.getByRole("status")).toHaveText(`Exited with status ${native.status}`, { timeout: 20000 });
    expect(await page.locator("#stdout").textContent()).toBe(native.stdout);
    expect(await page.locator("#stderr").textContent()).toBe(native.stderr);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

test("runs Hello and Status lookup, then reloads the multi-file draft", async ({ page }) => {
  await openEditor(page);
  await expect(page.getByRole("button", { name: "Build", exact: true })).toHaveCount(0);
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

for (const example of ["fibonacci", "factorial", "rule110"]) {
  test(`runs the ${example} example with native output`, async ({ page }) => {
    await openEditor(page);
    page.once("dialog", (dialog) => void dialog.accept());
    await page.getByLabel("Example").selectOption(example);
    await expect(page.locator("#filename")).toHaveValue(`${example}.b`);
    await compareWithNative(page, [`tests/programs/${example}.b`]);
  });
}

test("passes prefilled stdin and preserves stderr and a nonzero exit status", async ({ page }) => {
  await openEditor(page);
  await page.getByLabel("jBC source").fill(fixture("fixtures/input.b"));
  await page.getByLabel("Standard input").fill("Wasm\n");
  await compareWithNative(page, ["playground/tests/fixtures/input.b"], "Wasm\n");
});

test("reads a final input line without a newline and returns an empty value at EOF", async ({ page }) => {
  await openEditor(page);
  await page.getByLabel("jBC source").fill(fixture("fixtures/input-eof.b"));
  await page.getByLabel("Standard input").fill("last line");
  await compareWithNative(page, ["playground/tests/fixtures/input-eof.b"], "last line");
});

test("highlights the error line and column in an included file", async ({ page }) => {
  await openEditor(page);
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByLabel("Example").selectOption("status");
  await expect(page.locator("#filename")).toHaveValue("caller.b");
  await page.getByRole("button", { name: "I_STATUS", exact: true }).click();
  const editor = page.getByLabel("jBC source");
  const brokenInclude = await editor.inputValue() + fixture("fixtures/unsupported.b");
  await editor.fill(brokenInclude);
  await page.getByRole("button", { name: "caller.b", exact: true }).click();
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Build failed");
  await expect(page.locator("#diagnostics")).toContainText("PERFORM is unavailable in the browser");
  await expect(page.locator("#filename")).toHaveValue("I_STATUS");
  await expect(page.locator("#error-line")).toBeVisible();
  await expect(page.locator("#error-column")).toBeVisible();
  await expect(editor).toHaveAttribute("aria-invalid", "true");
  await page.getByRole("button", { name: "I_STATUS:3:12" }).click();
  await expect(editor).toBeFocused();
  expect(await editor.evaluate((source: HTMLTextAreaElement) => source.selectionStart)).toBe(brokenInclude.indexOf("PERFORM"));
  await editor.fill(fixture("../../tests/routines/I_STATUS"));
  await expect(page.locator("#error-line")).toBeHidden();
});

test("fills the desktop height, shows build time, and keeps the theme toggle accessible", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  await openEditor(page);
  const bottom = await page.getByRole("region", { name: "Project", exact: true })
    .evaluate((panel) => window.innerHeight - panel.getBoundingClientRect().bottom);
  expect(bottom).toBeLessThan(24);
  const buildTime = page.locator("#build-time");
  await expect(buildTime).toHaveText(/^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}$/);
  await expect(buildTime).toHaveAttribute("datetime", /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00Z$/);
  const light = page.getByRole("button", { name: "Switch to light theme", exact: true });
  await expect(light).toHaveText("☀︎");
  await light.click();
  await expect(page.getByRole("button", { name: "Switch to dark theme", exact: true })).toHaveText("☾");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
});

test("opens and dismisses playground help on desktop and mobile", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openEditor(page);
  const help = page.getByRole("button", { name: "Playground help" });
  await expect(page.locator("#stop + #help")).toBeVisible();
  await help.click();
  const dialog = page.getByRole("dialog", { name: "Playground help" });
  const close = dialog.getByRole("button", { name: "Close" });
  await expect(dialog).toBeVisible();
  await expect(close).toBeFocused();
  await expect(dialog.getByRole("heading", { name: "Link as routine" })).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Save, load, and back up projects" })).toBeVisible();
  await page.keyboard.press("Control+Enter");
  await expect(page.locator("#status")).toHaveText("Ready");
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(help).toBeFocused();

  await page.setViewportSize({ width: 390, height: 680 });
  await help.click();
  const box = await dialog.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.width).toBeLessThan(390);
  expect(box!.height).toBeLessThan(680);
  const lastParagraph = dialog.getByText("The browser also keeps a local draft", { exact: false }).filter({ visible: true });
  await lastParagraph.scrollIntoViewIfNeeded();
  await expect(lastParagraph).toBeInViewport();
  await close.click();
  await expect(dialog).toBeHidden();
  await expect(help).toBeFocused();
});

test("Stop terminates a running program and the next build succeeds", async ({ page }) => {
  await openEditor(page);
  await page.getByLabel("jBC source").fill(fixture("fixtures/loop.b"));
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Running…", { timeout: 20000 });
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
  const iframe = await page.evaluateHandle(async () => {
    const frame = document.createElement("iframe");
    frame.sandbox.add("allow-scripts");
    frame.src = "./runner.html";
    const loaded = new Promise<void>((resolve) => frame.addEventListener("load", () => resolve(), { once: true }));
    document.body.append(frame);
    await loaded;
    return frame;
  });
  const frame = await iframe.asElement()?.contentFrame();
  expect(frame).not.toBeNull();
  expect(await frame!.evaluate(async (url) => {
    let storage = "allowed";
    let network = "allowed";
    try { void localStorage; } catch { storage = "blocked"; }
    try { await fetch(url); } catch { network = "blocked"; }
    return { origin, storage, network };
  }, new URL("./examples/hello.b", page.url()).href)).toEqual({
    origin: "null", storage: "blocked", network: "blocked",
  });
});
