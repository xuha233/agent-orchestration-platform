export type DesktopAppHealth = {
  version: string;
  platform: string;
  workspace_count: number;
  available_agents: number;
  available_providers: number;
};

export type DesktopProjectSummary = {
  project_id: string;
  name: string;
  project_path: string;
  primary_agent: string;
  last_active: string;
  session_id?: string | null;
  latest_run_id: string;
  latest_run_status: string;
  latest_run_phase: string;
  latest_run_completion: string;
  needs_follow_up: boolean;
  attention_tags: string[];
  priority_rank: number;
  triage_summary: string;
  triage_evidence: string[];
};

export type DesktopProviderStatus = {
  provider_id: string;
  label: string;
  detected: boolean;
  auth_ok: boolean;
  binary_path?: string | null;
  version?: string | null;
  reason: string;
  install_commands: string[];
  required_env_vars: string[];
  configured_env_vars: string[];
  missing_env_vars: string[];
  stored_env_vars: Record<string, string>;
  preferred: boolean;
};

export type DesktopInstallResult = {
  provider_id: string;
  command: string;
  success: boolean;
  summary: string;
  output: string;
  next_steps: string[];
};

export type DesktopSetupCheck = {
  check_id: string;
  label: string;
  detected: boolean;
  required: boolean;
  version: string;
  reason: string;
  install_hint: string;
  install_commands: string[];
};

export type DesktopSetupInstallResult = {
  check_id: string;
  command: string;
  success: boolean;
  summary: string;
  output: string;
  next_steps: string[];
};

export type DesktopMemoryStatus = {
  project_id: string;
  project_path: string;
  enabled: boolean;
  global_enabled: boolean;
  project_enabled: boolean;
  backend: string;
  mem0_available: boolean;
  current_backend: string;
  total_memories: number;
  legacy_entry_count: number;
  migration_ready: boolean;
  migration_issues: string[];
  memory_sources: Record<string, number>;
  init_error: string;
};

export type DesktopMemoryRecord = {
  memory_id: string;
  content: string;
  memory_type: string;
  phase: string;
  run_id: string;
  timestamp: string;
};

export type DesktopMemoryMigrationResult = {
  project_id: string;
  dry_run: boolean;
  success: boolean;
  total_migrated: number;
  source_counts: Record<string, number>;
  errors: string[];
};

export type DesktopMemorySettings = {
  project_id: string;
  global_enabled: boolean;
  project_enabled: boolean;
  effective_enabled: boolean;
  backend: string;
  search_top_k: number;
  search_threshold: number;
  embedding_model: string;
  embedding_dims: number;
};

export type WorkflowRunSummary = {
  run_id: string;
  status: string;
  current_phase: string;
  original_input: string;
  clarified_summary: string;
  success_criteria: string[];
  hypothesis_ids: string[];
  created_at: string;
  updated_at: string;
  verification_verdict: string;
  completion_status: string;
  has_gaps: boolean;
  has_guardrails: boolean;
  attention_tags: string[];
  priority_rank: number;
  triage_summary: string;
  triage_evidence: string[];
};

export type WorkflowArtifactDocument = {
  filename: string;
  title: string;
  content: string;
  exists: boolean;
  metadata: Record<string, unknown>;
};

export type WorkflowRunDetail = {
  summary: WorkflowRunSummary;
  artifacts: WorkflowArtifactDocument[];
};

export type DesktopRunLaunchResult = {
  project_id: string;
  sprint_id: string;
  success: boolean;
  state: string;
  summary: string;
  next_steps: string[];
};

export type DesktopRunJob = {
  job_id: string;
  project_id: string;
  prompt: string;
  status: string;
  created_at: string;
  updated_at: string;
  sprint_id: string;
  summary: string;
  state: string;
  next_steps: string[];
  error: string;
};
