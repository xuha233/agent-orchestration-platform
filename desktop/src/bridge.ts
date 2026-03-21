import { invoke } from "@tauri-apps/api/core";

type BridgeEnvelope<T> = {
  ok: boolean;
  data?: T;
  error?: string;
};

type BridgePayload = {
  project_id?: string;
  run_id?: string;
  job_id?: string;
  limit?: number;
  provider_id?: string;
  env_values?: Record<string, string>;
  preferred?: boolean;
  prompt?: string;
  project_name?: string;
  project_path?: string;
  primary_agent?: string;
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
  create_project: {
    project_id: "mock-project",
    name: "Mock Project",
    project_path: "C:/mock/project",
    primary_agent: "codex",
    last_active: "",
    session_id: null,
    latest_run_id: "",
    latest_run_status: "",
    latest_run_phase: "",
    latest_run_completion: "",
    needs_follow_up: false,
  },
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
  start_run_async: {
    job_id: "job-mock-001",
    project_id: "mock-project",
    prompt: "Mock prompt",
    status: "queued",
    created_at: "2026-03-22T00:00:00Z",
    updated_at: "2026-03-22T00:00:00Z",
    sprint_id: "",
    summary: "",
    state: "",
    next_steps: [],
    error: "",
  },
  run_job_status: {
    job_id: "job-mock-001",
    project_id: "mock-project",
    prompt: "Mock prompt",
    status: "completed",
    created_at: "2026-03-22T00:00:00Z",
    updated_at: "2026-03-22T00:00:10Z",
    sprint_id: "mock-sprint",
    summary: "Mock desktop run completed.",
    state: "completed",
    next_steps: ["Inspect workflow artifacts"],
    error: "",
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
    jobId: payload.job_id,
    limit: payload.limit,
    providerId: payload.provider_id,
    envValues: payload.env_values,
    preferred: payload.preferred,
    prompt: payload.prompt,
    projectName: payload.project_name,
    projectPath: payload.project_path,
    primaryAgent: payload.primary_agent,
  });
  const envelope = JSON.parse(raw) as BridgeEnvelope<T>;
  if (!envelope.ok || envelope.data === undefined) {
    throw new Error(envelope.error || `Bridge call failed for action: ${action}`);
  }
  return envelope.data;
}
