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
