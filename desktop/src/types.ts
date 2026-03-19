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
