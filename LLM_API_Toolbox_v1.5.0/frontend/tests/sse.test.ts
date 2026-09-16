import { describe, expect, it } from "vitest";
import { parseEventBlock, parseSSEStream } from "../lib/sse";

describe("SSE parser", () => {
  it("parses a named event", () => {
    expect(parseEventBlock('event: delta\ndata: {"delta":"你","seq":1}')).toEqual({
      event: "delta",
      data: { delta: "你", seq: 1 },
    });
  });

  it("handles event boundaries split across network chunks", async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('event: meta\ndata: {"seq":0}\n'));
        controller.enqueue(encoder.encode('\nevent: delta\ndata: {"delta":"OK","seq":1}\n\n'));
        controller.enqueue(encoder.encode('event: done\ndata: {"seq":2}'));
        controller.close();
      },
    });
    const events = [];
    for await (const event of parseSSEStream(stream)) events.push(event);
    expect(events.map((item) => item.event)).toEqual(["meta", "delta", "done"]);
    expect(events[1].data).toEqual({ delta: "OK", seq: 1 });
  });
});
