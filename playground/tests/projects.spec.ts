import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

test.skip(!process.env.JBCC_PLAYGROUND_STATIC, "Exercises local browser projects");

const fixture = (path: string) => readFileSync(new URL(`../../tests/${path}`, import.meta.url), "utf8");
const source = (page: Page) => page.getByLabel("jBC source");
const name = (page: Page) => page.getByLabel("Project name");
const status = (page: Page) => page.locator("#cloud-status");

async function open(page: Page) {
  await page.goto("/");
  await expect(page.locator("#filename")).toHaveValue("hello.b");
}

async function save(page: Page, project: string) {
  await name(page).fill(project);
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(status(page)).toHaveText(`Autosaving ${project}`);
}

function recoveryRevision(page: Page) {
  return page.evaluate(() => JSON.parse(localStorage.getItem("jbcc.playground.draft") ?? "{}").localProject?.revision);
}

test("debounces named autosaves and flushes the draft on reload", async ({ page }) => {
  await open(page);
  await save(page, "hello-work");
  await expect.poll(() => recoveryRevision(page)).toBe(1);
  const hello = await source(page).inputValue();
  await source(page).press("End");
  await source(page).pressSequentially("   ");
  const edited = await source(page).inputValue();
  expect(edited).not.toBe(hello);
  await expect.poll(() => recoveryRevision(page)).toBe(2);
  await page.reload();
  await expect(name(page)).toHaveValue("hello-work");
  await expect(source(page)).toHaveValue(edited);
  await expect(status(page)).toHaveText("Autosaving hello-work");

  const immediate = edited + "\n";
  await source(page).fill(immediate);
  await page.reload();
  await expect(source(page)).toHaveValue(immediate);
  await expect.poll(() => recoveryRevision(page)).toBe(3);
});

test("selecting a name only fills the field, then Load opens the saved project", async ({ page }) => {
  await open(page);
  await save(page, "hello-copy");
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByLabel("Example").selectOption("fibonacci");
  await expect(page.locator("#filename")).toHaveValue("fibonacci.b");
  await save(page, "fibonacci-copy");
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByLabel("Example").selectOption("factorial");
  await expect(page.locator("#filename")).toHaveValue("factorial.b");

  await page.getByRole("region", { name: "Project", exact: true }).getByText("Projects", { exact: true }).click();
  await page.getByRole("button", { name: "fibonacci-copy", exact: true }).click();
  await expect(name(page)).toHaveValue("fibonacci-copy");
  await expect(source(page)).toHaveValue(fixture("programs/factorial.b"));
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByRole("button", { name: "Load", exact: true }).click();
  await expect(source(page)).toHaveValue(fixture("programs/fibonacci.b"));
});

test("exports and imports files, linked routines, and stdin in another browser profile", async ({ browser, page }) => {
  await open(page);
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByLabel("Example").selectOption("status");
  await expect(page.locator("#filename")).toHaveValue("caller.b");
  await page.getByRole("button", { name: "get.status.b", exact: true }).click();
  await page.getByLabel("Standard input").fill("saved input");
  await save(page, "status-example");

  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export", exact: true }).click();
  const download = await downloaded;
  expect(download.suggestedFilename()).toBe("status-example.jbc-project.json");
  const file = await download.path();
  const other = await browser.newContext();
  try {
    const target = await other.newPage();
    await open(target);
    target.once("dialog", (dialog) => void dialog.accept());
    await target.locator("#project-file").setInputFiles(file);
    await expect(name(target)).toHaveValue("status-example");
    await expect(target.locator("#filename")).toHaveValue("get.status.b");
    await expect(target.getByLabel("Main", { exact: true })).toHaveValue("caller.b");
    await expect(target.getByLabel("Link as routine")).toBeChecked();
    await expect(target.getByRole("button", { name: "I_STATUS", exact: true })).toBeVisible();
    await expect(target.getByLabel("Standard input")).toHaveValue("saved input");

    target.once("dialog", (dialog) => void dialog.dismiss());
    await target.locator("#project-file").setInputFiles(file);
    await expect(target.getByRole("button", { name: "Import", exact: true })).toBeEnabled();
    await expect(source(target)).toHaveValue(fixture("routines/get.status.b"));
    await target.locator("#project-file").setInputFiles({
      name: "invalid.json", mimeType: "application/json", buffer: Buffer.from('{"version":2}'),
    });
    await expect(status(target)).toHaveText("Unsupported project file version");
    await expect(target.locator("#filename")).toHaveValue("get.status.b");
  } finally {
    await other.close();
  }
});

test("keeps the editor draft when a different tab saves a newer revision", async ({ context, page }) => {
  await open(page);
  await save(page, "shared");
  const second = await context.newPage();
  await open(second);
  await expect(status(second)).toHaveText("Autosaving shared");
  await source(page).fill(fixture("programs/fibonacci.b"));
  await expect.poll(() => recoveryRevision(page)).toBe(2);
  await source(second).fill(fixture("programs/factorial.b"));
  await expect(status(second)).toHaveText("Project changed in another tab. Your draft was kept");
  await expect(source(second)).toHaveValue(fixture("programs/factorial.b"));
  second.once("dialog", (dialog) => void dialog.accept());
  await second.getByRole("button", { name: "Load", exact: true }).click();
  await expect(source(second)).toHaveValue(fixture("programs/fibonacci.b"));
});
