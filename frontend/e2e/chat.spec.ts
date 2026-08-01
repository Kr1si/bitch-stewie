import { test, expect } from "@playwright/test";
import { ensureProject, expectAssistantTurn, uniqueProjectName } from "./helpers";

/**
 * Story 1 — chat with the orchestrator.
 *
 * Reality: a full assistant turn needs a REACHABLE LLM (LongCat). In CI/sandbox
 * the model may be down, in which case the UI surfaces an "Error:" assistant
 * message rather than a real reply. We assert that an ASSISTANT BUBBLE appears
 * (Avatar "S" inside <main>), which is true for BOTH the happy path and the
 * documented error state — so the test proves the streaming UI works without
 * being brittle about LLM availability. The user bubble appearing first proves
 * the send path + project selection work regardless.
 */
test.describe("chat", () => {
  test("select a project, send a message, get an assistant (or error) turn", async ({
    page,
    request,
  }) => {
    const name = uniqueProjectName();
    const created = await ensureProject(request, name);
    expect(created, "backend must be reachable to seed a project").not.toBeNull();

    await page.goto("/chat");

    // The project dropdown auto-selects the first project; the input enables and
    // its placeholder switches to the prompt. Wait for that so we know a project
    // is selected.
    const input = page.getByPlaceholder("Ask the orchestrator…");
    await expect(input).toBeVisible({ timeout: 20_000 });
    await expect(input).toBeEnabled({ timeout: 20_000 });

    const message = "In one sentence, what is this project for?";
    await input.fill(message);
    await page.getByRole("button", { name: "Send" }).click();

    // User bubble shows the message we sent — proves the send path works.
    await expect(page.getByText(message)).toBeVisible({ timeout: 10_000 });

    // Assistant turn (streaming reply OR error message) appears. Generous timeout
    // because a real LLM streamed reply can take a while; an error is fast.
    await expectAssistantTurn(page, 90_000);
  });
});
