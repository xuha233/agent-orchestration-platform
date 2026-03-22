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
  check_id?: string;
  dry_run?: boolean;
  global_enabled?: boolean;
  project_enabled?: boolean;
  backend?: string;
  search_top_k?: number;
  search_threshold?: number;
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
  setup_status: [
    {
      check_id: "python",
      label: "Python",
      detected: true,
      required: true,
      version: "Python 3.12.0",
      reason: "",
      install_hint: "Install Python 3.11+ and keep it on PATH for the desktop sidecar.",
      install_commands: ["winget install Python.Python.3.11"],
    },
    {
      check_id: "cargo",
      label: "Cargo",
      detected: false,
      required: false,
      version: "",
      reason: "Cargo was not found on PATH.",
      install_hint: "Install Cargo via rustup to build native desktop packages.",
      install_commands: ["winget install Rustlang.Rustup"],
    },
  ],
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
    attention_tags: [],
    priority_rank: 0,
    triage_summary: "",
    triage_evidence: [],
  },
  memory_status: {
    project_id: "mock-project",
    project_path: "C:/mock/project",
    enabled: true,
    global_enabled: true,
    project_enabled: true,
    backend: "file",
    mem0_available: false,
    current_backend: "file",
    total_memories: 2,
    legacy_entry_count: 1,
    migration_ready: false,
    migration_issues: ["mem0 unavailable in mock bridge"],
    memory_sources: { hypotheses: 0, learnings: 0, project_memory: 1 },
    init_error: "",
  },
  memory_records: [
    {
      memory_id: "mem-001",
      content: "Workflow completion for mock run",
      memory_type: "workflow_completion",
      phase: "complete",
      run_id: "mock-sprint",
      timestamp: "2026-03-22T00:00:00Z",
    },
  ],
  memory_migrate: {
    project_id: "mock-project",
    dry_run: true,
    success: true,
    total_migrated: 1,
    source_counts: { hypotheses: 0, learnings: 0, project_memory: 1 },
    errors: [],
  },
  memory_settings: {
    project_id: "mock-project",
    global_enabled: true,
    project_enabled: true,
    effective_enabled: true,
    backend: "file",
    search_top_k: 5,
    search_threshold: 0.7,
    embedding_model: "text-embedding-3-small",
    embedding_dims: 1536,
  },
  memory_update_settings: {
    project_id: "mock-project",
    global_enabled: true,
    project_enabled: true,
    effective_enabled: true,
    backend: "mem0_local",
    search_top_k: 8,
    search_threshold: 0.6,
    embedding_model: "text-embedding-3-small",
    embedding_dims: 1536,
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
  install_provider: {
    provider_id: "mock",
    command: "npm install -g mock",
    success: true,
    summary: "Mock install completed.",
    output: "installed",
    next_steps: ["mock auth login"],
  },
  install_setup_dependency: {
    check_id: "cargo",
    command: "winget install Rustlang.Rustup",
    success: true,
    summary: "Cargo install completed.",
    output: "installed",
    next_steps: [],
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
    checkId: payload.check_id,
    dryRun: payload.dry_run,
    globalEnabled: payload.global_enabled,
    projectEnabled: payload.project_enabled,
    backend: payload.backend,
    searchTopK: payload.search_top_k,
    searchThreshold: payload.search_threshold,
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
