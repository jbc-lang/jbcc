import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const fixture = (path: string) => readFileSync(new URL(`fixtures/includes/${path}`, import.meta.url), "utf8");
const file = (path: string) => ({ path, source: fixture(path) });
async function openProject(page: Page, entry: string, files: { path: string; source: string }[], units: string[] = []) {
  await page.addInitScript((draft) => {
    localStorage.setItem("jbcc.playground.draft", JSON.stringify(draft));
  }, { files, entry, units, active: entry, stdin: "" });
  await page.goto("/");
}

async function expectDiagnostic(page: Page, message: string) {
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.locator("#status")).toHaveText("Build failed", { timeout: 20000 });
  await expect(page.locator("#diagnostics")).toContainText(message);
}

test("compiles nested and case-sensitive includes with shared files and relative precedence", async ({ page }) => {
  const paths = ["app/main.b", "app/I_CHOICE", "I_CHOICE", "I_SHARED", "library/show.b", "library/defs/I_NESTED"];
  const files = paths.map(file);
  await openProject(page, "app/main.b", files, ["library/show.b"]);
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Exited with status 0", { timeout: 20000 });
  expect(await page.locator("#stdout").textContent()).toBe("shared-local\nshared\n");

  await page.getByRole("button", { name: "I_SHARED", exact: true }).click();
  const path = page.getByLabel("Path", { exact: true });
  await path.fill("I_shared");
  await path.press("Enter");
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.locator("#diagnostics")).toContainText("include file 'I_SHARED' not found");
  await expect(page.locator("#filename")).toHaveValue("library/defs/I_NESTED");
});

for (const [entry, paths, origin, message] of [
  ["missing.b", ["missing.b"], "missing.b", "include file 'Missing' not found"],
  ["first.b", ["first.b", "second.b"], "second.b", "recursive include 'first.b'"],
  ["app/escape.b", ["app/escape.b"], "app/escape.b", "include escapes project root"],
  ["app/root-fallback.b", ["app/root-fallback.b"], "app/root-fallback.b", "include file '../program.c' not found"],
] as const) {
  test(`reports the include failure in ${entry}`, async ({ page }) => {
    await openProject(page, entry, paths.map(file));
    await expectDiagnostic(page, message);
    await expect(page.locator("#filename")).toHaveValue(origin);
  });
}

const main = file("missing.b");
const invalid = [
  [[main, main], "duplicate project file path"],
  [[main, { ...main, path: "../outside" }], "invalid project file path"],
  [[main, { ...main, path: "missing.b/child" }], "file path conflicts with a project directory"],
  [[{ ...main, source: "x".repeat(65537) }], "source exceeds project size limit"],
] as const;

for (const [files, message] of invalid) {
  test(`rejects a workspace with ${message}`, async ({ page }) => {
    await openProject(page, main.path, [...files]);
    await expectDiagnostic(page, message);
  });
}

test("enforces the include depth limit", async ({ page }) => {
  const chain = Array.from({ length: 18 }, (_, index) => ({
    path: `I${index}`,
    source: index === 17 ? "" : `$INSERT I${index + 1}\n`,
  }));
  await openProject(page, "I0", chain);
  await expectDiagnostic(page, "include depth limit exceeded");
});

test("enforces the expanded source limit", async ({ page }) => {
  await openProject(page, "main.b", [
    { path: "main.b", source: "$INSERT BIG\n".repeat(18) },
    { path: "BIG", source: ("* " + "x".repeat(1021) + "\n").repeat(64) },
  ]);
  await expectDiagnostic(page, "expanded source limit exceeded");
});
