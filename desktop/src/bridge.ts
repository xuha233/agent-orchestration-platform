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
  provider_id?: string;
  env_values?: Record<string, string>;
  preferred?: boolean;
  prompt?: string;
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
  update_provider: {
    provider_id: "mock",
    label: "Mock",
    detected: false,
    auth_ok: false,
    binary_path: null,
    version: null,
    reason: "",
    install_commands: [],
    required_env_vars: [],
    configured_env_vars: [],
    missing_env_vars: [],
    stored_env_vars: {},
    preferred: false,
  },
  start_run: {
    project_id: "mock-project",
    sprint_id: "mock-sprint",
    success: true,
    state: "completed",
    summary: "Mock desktop run completed.",
    next_steps: ["Inspect workflow artifacts"],
  },
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
    providerId: payload.provider_id,
    envValues: payload.env_values,
    preferred: payload.preferred,
    prompt: payload.prompt,
  });
  const envelope = JSON.parse(raw) as BridgeEnvelope<T>;
  if (!envelope.ok || envelope.data === undefined) {
    throw new Error(envelope.error || `Bridge call failed for action: ${action}`);
  }
  return envelope.data;
}
