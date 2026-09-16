import { expect, test } from "@playwright/test";

test("completes a streamed Mock conversation", async ({ page }) => {
  await page.route("**/api/v1/providers", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        providers: [{
          name: "mock",
          display_name: "Mock",
          status: "available",
          reason_code: null,
          capabilities: ["text", "streaming"],
        }],
      }),
    }),
  );
  await page.route("**/api/v1/models?provider=mock", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        models: [{
          id: "mock-echo-v1",
          display_name: "Mock Echo v1",
          provider: "mock",
          capabilities: ["text", "streaming"],
          default: true,
          max_output_tokens: 8192,
        }],
      }),
    }),
  );
  await page.route("**/api/v1/chat/completions/stream", (route) =>
    route.fulfill({
      contentType: "text/event-stream",
      body: [
        'event: meta\ndata: {"request_id":"req_test","provider":"mock","model":"mock-echo-v1","seq":0}\n\n',
        'event: delta\ndata: {"delta":"测试成功","seq":1}\n\n',
        'event: done\ndata: {"finish_reason":"stop","usage":{"input_tokens":2,"output_tokens":4,"total_tokens":6},"seq":2}\n\n',
      ].join(""),
    }),
  );

  await page.goto("/");
  await expect(page.getByText("Mock Echo v1")).toBeVisible();
  await page.getByLabel("对话消息").fill("你好");
  await page.getByRole("button", { name: /发送消息/ }).click();
  await expect(page.getByText("测试成功")).toBeVisible();
  await expect(page.getByText(/输入 2 · 输出 4 tokens/)).toBeVisible();
});

