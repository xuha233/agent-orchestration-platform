import { invoke } from "@tauri-apps/api/core";

type BridgeEnvelope<T> = {
  ok: boolean;
  data?: T;
  error?: string;
};

type BridgePayload = {
  project_id?: string;
  run_id?: string;
  limit?: number;
};

const mockBridgeData = {
  health: {
    version: "0.5.0",
    platform: "desktop-dev",
    workspace_count: 0,
    available_agents: 0,
    available_providers: 0,
  },
  projects: [],
  providers: [],
  runs: [],
};

export async function invokeAppRuntime<T>(action: string, payload: BridgePayload = {}): Promise<T> {
  const isTauri = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

  if (!isTauri) {
    return mockBridgeData[action as keyof typeof mockBridgeData] as T;
  }

  const raw = await invoke<string>("app_runtime", {
    action,
    projectId: payload.project_id,
    runId: payload.run_id,
    limit: payload.limit,
  });
  const envelope = JSON.parse(raw) as BridgeEnvelope<T>;
  if (!envelope.ok || envelope.data === undefined) {
    throw new Error(envelope.error || `Bridge call failed for action: ${action}`);
  }
  return envelope.data;
}
