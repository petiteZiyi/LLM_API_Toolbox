import type { ModelInfo } from "./types";

export function selectModelAfterConfig(models: ModelInfo[], currentModel: string) {
  const preserved = models.some((item) => item.id === currentModel);
  const fallback = models.find((item) => item.default)?.id ?? models[0]?.id ?? "";
  return { model: preserved ? currentModel : fallback, preserved };
}
