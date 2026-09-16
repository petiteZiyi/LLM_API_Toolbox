import { describe, expect, it } from "vitest";
import { selectModelAfterConfig } from "../lib/model-selection";
import type { ModelInfo } from "../lib/types";

function model(id: string, isDefault = false): ModelInfo {
  return {
    id,
    display_name: id,
    provider: "deepseek",
    capabilities: ["text", "streaming"],
    default: isDefault,
    max_output_tokens: null,
  };
}

describe("selectModelAfterConfig", () => {
  it("preserves the current model when it still exists", () => {
    expect(selectModelAfterConfig([model("a", true), model("b")], "b")).toEqual({
      model: "b",
      preserved: true,
    });
  });

  it("falls back to the default model when the current model was removed", () => {
    expect(selectModelAfterConfig([model("a", true), model("b")], "removed")).toEqual({
      model: "a",
      preserved: false,
    });
  });

  it("returns an empty model for an empty configuration", () => {
    expect(selectModelAfterConfig([], "removed")).toEqual({ model: "", preserved: false });
  });
});
