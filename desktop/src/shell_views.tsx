import { useMemo } from "react";
import type { Dispatch, SetStateAction } from "react";

import type {
  DesktopAppHealth,
  DesktopInstallResult,
  DesktopProjectSummary,
  DesktopProviderStatus,
  DesktopSetupCheck,
  DesktopSetupInstallResult,
} from "./types";
import { EmptyState, MetricCard, SummaryItem } from "./ui";

const setupGuideUrls: Record<string, string> = {
  python: "https://www.python.org/downloads/",
  node: "https://nodejs.org/en/download",
  npm: "https://docs.npmjs.com/downloading-and-installing-node-js-and-npm",
  rustc: "https://www.rust-lang.org/tools/install",
  cargo: "https://www.rust-lang.org/tools/install",
};

async function copyText(value: string) {
  if (typeof navigator === "undefined" || !navigator.clipboard) {
    return;
  }
  await navigator.clipboard.writeText(value);
}

type HomeWorkspaceProps = {
  loadState: "idle" | "loading" | "ready" | "error";
  health: DesktopAppHealth | null;
  error: string;
  statusMessage: string;
  projects: DesktopProjectSummary[];
  runsCount: number;
  selectedProject: DesktopProjectSummary | null;
  preferredProvider: DesktopProviderStatus | null;
  followUpProjects: DesktopProjectSummary[];
  providers: DesktopProviderStatus[];
  setActiveView: (view: "projects" | "providers" | "run") => void;
};

export function HomeWorkspace(props: HomeWorkspaceProps) {
  const {
    loadState,
    health,
    error,
    statusMessage,
    projects,
    runsCount,
    selectedProject,
    preferredProvider,
    followUpProjects,
    providers,
    setActiveView,
  } = props;
  const providerReady = Boolean(
    preferredProvider?.detected && preferredProvider.missing_env_vars.length === 0,
  );
  const onboardingSteps = [
    {
      label: "Choose provider",
      done: providerReady,
      hint: providerReady
        ? `${preferredProvider?.label} is ready`
        : preferredProvider
          ? `${preferredProvider.label} still needs setup`
          : "Pick a preferred provider first",
      action: "providers" as const,
    },
    {
      label: "Register project",
      done: projects.length > 0,
      hint: projects.length > 0 ? `${projects.length} project(s) connected` : "Add your first project folder",
      action: "projects" as const,
    },
    {
      label: "Run workflow",
      done: runsCount > 0,
      hint: runsCount > 0 ? `${runsCount} workflow run(s) recorded` : "Start your first run from desktop",
      action: "run" as const,
    },
  ];
  const recommendedProvider =
    providers.find((provider) => provider.detected && provider.missing_env_vars.length === 0) ?? null;

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">AOP Desktop</p>
          <h1>Idea to MVP workflows, now shaped like a real local app.</h1>
          <p className="lede">
            The desktop MVP already reads live project, provider, and workflow artifact data
            from the Python runtime bridge.
          </p>
        </div>
        <div className="hero-status">
          <div className="status-panel">
            <span className={`pill ${loadState === "ready" ? "pill-good" : loadState === "error" ? "pill-bad" : "pill-warn"}`}>
              {loadState}
            </span>
            <p className="status-label">Runtime bridge</p>
            <h2>{health ? `v${health.version}` : "Waiting"}</h2>
            <p className="status-subtle">{health ? `${health.platform} runtime detected` : "Starting local bridge..."}</p>
          </div>
        </div>
      </section>

      {error ? <section className="alert">{error}</section> : null}
      {statusMessage ? <section className="status-banner">{statusMessage}</section> : null}

      <section className="metrics">
        <MetricCard label="Projects" value={String(health?.workspace_count ?? projects.length)} />
        <MetricCard label="Agents" value={String(health?.available_agents ?? 0)} />
        <MetricCard label="Providers" value={String(health?.available_providers ?? 0)} />
        <MetricCard label="Runs" value={String(runsCount)} />
      </section>

      <section className="grid">
        <article className="panel panel-wide">
          <div className="panel-head">
            <div>
              <p className="panel-eyebrow">Focus</p>
              <h2>What to do next</h2>
            </div>
          </div>
          <div className="summary-row">
            <SummaryItem label="Selected project" value={selectedProject?.name || "None"} />
            <SummaryItem label="Preferred provider" value={preferredProvider?.label || "Unset"} />
            <SummaryItem label="Follow-up projects" value={String(followUpProjects.length)} />
            <SummaryItem label="Latest run" value={selectedProject?.latest_run_id || "-"} />
          </div>
          <div className="provider-actions">
            <button type="button" className="action-button" onClick={() => setActiveView("projects")}>
              Open projects
            </button>
            <button type="button" className="action-button" onClick={() => setActiveView("providers")}>
              Configure providers
            </button>
            <button type="button" className="action-button action-button-accent" onClick={() => setActiveView("run")}>
              Start a run
            </button>
          </div>
        </article>

        <article className="panel">
          <div className="panel-head">
            <div>
              <p className="panel-eyebrow">Follow-up</p>
              <h2>Project queue</h2>
            </div>
          </div>
          {followUpProjects.length > 0 ? (
            <div className="provider-command-list">
              {followUpProjects.slice(0, 4).map((project) => (
                <code key={project.project_id}>{project.name} - {project.latest_run_phase || "no phase"}</code>
              ))}
            </div>
          ) : (
            <EmptyState title="Queue is clear" body="No projects currently need follow-up from the latest workflow run." />
          )}
        </article>
      </section>

      <section className="grid onboarding-grid">
        <article className="panel panel-wide">
          <div className="panel-head">
            <div>
              <p className="panel-eyebrow">Onboarding</p>
              <h2>Get to first useful run</h2>
            </div>
          </div>
          <div className="onboarding-list">
            {onboardingSteps.map((step) => (
              <button
                key={step.label}
                type="button"
                className={`onboarding-step ${step.done ? "onboarding-step-done" : ""}`}
                onClick={() => setActiveView(step.action)}
              >
                <span className={`pill ${step.done ? "pill-good" : "pill-warn"}`}>{step.done ? "Done" : "Next"}</span>
                <strong>{step.label}</strong>
                <p>{step.hint}</p>
              </button>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-head">
            <div>
              <p className="panel-eyebrow">Recommendation</p>
              <h2>Best next move</h2>
            </div>
          </div>
          <div className="provider-command-list">
            <code>
              {providerReady
                ? `Launch the next run for ${selectedProject?.name || "your selected project"}`
                : recommendedProvider
                  ? `Set ${recommendedProvider.label} as preferred and finish provider setup`
                  : "Open Providers and finish the first available setup path"}
            </code>
          </div>
          <div className="provider-actions">
            <button
              type="button"
              className="action-button action-button-accent"
              onClick={() => setActiveView(providerReady ? "run" : "providers")}
            >
              {providerReady ? "Open run workspace" : "Open provider setup"}
            </button>
          </div>
        </article>
      </section>
    </>
  );
}

type ProjectsWorkspaceProps = {
  projects: DesktopProjectSummary[];
  selectedProjectId: string;
  setSelectedProjectId: (projectId: string) => void;
  statusMessage: string;
  prioritizedProjects: DesktopProjectSummary[];
  projectNameDraft: string;
  setProjectNameDraft: (value: string) => void;
  projectPathDraft: string;
  setProjectPathDraft: (value: string) => void;
  projectAgentDraft: string;
  setProjectAgentDraft: (value: string) => void;
  createProject: () => Promise<void>;
  projectSubmitting: boolean;
  selectedProject: DesktopProjectSummary | null;
  focusProject: (projectId: string, nextView: "projects" | "run" | "workflow") => void;
};

export function ProjectsWorkspace(props: ProjectsWorkspaceProps) {
  const {
    projects,
    selectedProjectId,
    setSelectedProjectId,
    statusMessage,
    prioritizedProjects,
    projectNameDraft,
    setProjectNameDraft,
    projectPathDraft,
    setProjectPathDraft,
    projectAgentDraft,
    setProjectAgentDraft,
    createProject,
    projectSubmitting,
    selectedProject,
    focusProject,
  } = props;

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <p className="panel-eyebrow">Projects</p>
          <h2>Register and inspect workspaces</h2>
        </div>
      </div>

      <div className="project-toolbar">
        <label htmlFor="project-select">Selected project</label>
        <select
          id="project-select"
          value={selectedProjectId}
          onChange={(event) => setSelectedProjectId(event.target.value)}
        >
          {projects.length === 0 ? <option value="">No projects found</option> : null}
          {projects.map((project) => (
            <option key={project.project_id} value={project.project_id}>
              {project.name}
            </option>
          ))}
        </select>
      </div>
      {statusMessage ? <section className="status-banner">{statusMessage}</section> : null}

      {prioritizedProjects.length > 0 ? (
        <div className="project-priority-strip">
          {prioritizedProjects.slice(0, 3).map((project) => (
            <button
              key={project.project_id}
              type="button"
              className={`project-priority-card ${selectedProjectId === project.project_id ? "project-priority-card-active" : ""}`}
              onClick={() => setSelectedProjectId(project.project_id)}
            >
              <div className="run-top">
                <div>
                  <h3>{project.name}</h3>
                  <p>{project.needs_follow_up ? "Needs follow-up" : "Ready for the next run"}</p>
                </div>
                <span className={`pill ${project.needs_follow_up ? "pill-warn" : "pill-good"}`}>
                  {project.latest_run_phase || "idle"}
                </span>
              </div>
              <div className="summary-row">
                <SummaryItem label="Run" value={project.latest_run_id || "-"} />
                <SummaryItem label="Status" value={project.latest_run_status || "-"} />
                <SummaryItem label="Completion" value={project.latest_run_completion || "-"} />
                <SummaryItem label="Agent" value={project.primary_agent} />
              </div>
            </button>
          ))}
        </div>
      ) : null}

      <div className="project-register">
        <div className="panel-head">
          <div>
            <p className="panel-eyebrow">Register project</p>
            <h2>Add an existing folder</h2>
          </div>
        </div>
        <div className="project-register-grid">
          <label className="provider-field">
            <span>Name</span>
            <input
              type="text"
              value={projectNameDraft}
              placeholder="Optional project label"
              onChange={(event) => setProjectNameDraft(event.target.value)}
            />
          </label>
          <label className="provider-field provider-field-wide">
            <span>Path</span>
            <input
              type="text"
              value={projectPathDraft}
              placeholder="G:\\path\\to\\project"
              onChange={(event) => setProjectPathDraft(event.target.value)}
            />
          </label>
          <label className="provider-field">
            <span>Primary agent</span>
            <select value={projectAgentDraft} onChange={(event) => setProjectAgentDraft(event.target.value)}>
              <option value="codex">Codex</option>
              <option value="claude_code">Claude Code</option>
              <option value="opencode">OpenCode</option>
            </select>
          </label>
        </div>
        <div className="provider-actions">
          <button
            type="button"
            className="action-button action-button-accent"
            onClick={() => void createProject()}
            disabled={projectSubmitting}
          >
            {projectSubmitting ? "Registering..." : "Register project"}
          </button>
        </div>
      </div>

      {selectedProject ? (
        <div className="project-summary">
          <div>
            <p className="panel-eyebrow">Path</p>
            <h3>{selectedProject.project_path}</h3>
          </div>
          <div className="summary-row">
            <SummaryItem label="Primary agent" value={selectedProject.primary_agent} />
            <SummaryItem label="Latest run" value={selectedProject.latest_run_id || "-"} />
            <SummaryItem label="Phase" value={selectedProject.latest_run_phase || "-"} />
            <SummaryItem label="Completion" value={selectedProject.latest_run_completion || "-"} />
          </div>
          <div className="provider-actions">
            <button
              type="button"
              className="action-button"
              onClick={() => focusProject(selectedProject.project_id, "workflow")}
            >
              Open workflow
            </button>
            <button
              type="button"
              className="action-button action-button-accent"
              onClick={() => focusProject(selectedProject.project_id, "run")}
            >
              Start next run
            </button>
          </div>
        </div>
      ) : (
        <EmptyState title="No project selected" body="Create or register a workspace to see desktop project summaries here." />
      )}

      {prioritizedProjects.length > 0 ? (
        <div className="project-list-grid">
          {prioritizedProjects.map((project) => (
            <article key={project.project_id} className="project-list-card">
              <div className="run-top">
                <div>
                  <p className="panel-eyebrow">Project</p>
                  <h3>{project.name}</h3>
                </div>
                <span className={`pill ${project.needs_follow_up ? "pill-warn" : "pill-good"}`}>
                  {project.needs_follow_up ? "Follow-up" : "Stable"}
                </span>
              </div>
              <div className="summary-row">
                <SummaryItem label="Run" value={project.latest_run_id || "-"} />
                <SummaryItem label="Phase" value={project.latest_run_phase || "-"} />
                <SummaryItem label="Status" value={project.latest_run_status || "-"} />
                <SummaryItem label="Agent" value={project.primary_agent} />
              </div>
              <div className="provider-actions">
                <button
                  type="button"
                  className="action-button"
                  onClick={() => focusProject(project.project_id, "projects")}
                >
                  Inspect
                </button>
                <button
                  type="button"
                  className="action-button"
                  onClick={() => focusProject(project.project_id, "workflow")}
                >
                  Workflow
                </button>
                <button
                  type="button"
                  className="action-button action-button-accent"
                  onClick={() => focusProject(project.project_id, "run")}
                >
                  Run
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

type ProvidersWorkspaceProps = {
  statusMessage: string;
  providers: DesktopProviderStatus[];
  providerDrafts: Record<string, Record<string, string>>;
  setProviderDrafts: Dispatch<SetStateAction<Record<string, Record<string, string>>>>;
  saveProviderConfig: (providerId: string, preferred: boolean) => Promise<void>;
  installProviderDependency: (providerId: string) => Promise<DesktopInstallResult | null>;
  installingProviderId: string;
  lastInstallResult: DesktopInstallResult | null;
};

export function ProvidersWorkspace(props: ProvidersWorkspaceProps) {
  const {
    statusMessage,
    providers,
    providerDrafts,
    setProviderDrafts,
    saveProviderConfig,
    installProviderDependency,
    installingProviderId,
    lastInstallResult,
  } = props;
  const sortedProviders = useMemo(() => {
    return [...providers].sort((left, right) => {
      if (left.preferred !== right.preferred) {
        return left.preferred ? -1 : 1;
      }
      const leftReady = Number(left.detected && left.missing_env_vars.length === 0);
      const rightReady = Number(right.detected && right.missing_env_vars.length === 0);
      if (leftReady !== rightReady) {
        return rightReady - leftReady;
      }
      if (left.detected !== right.detected) {
        return left.detected ? -1 : 1;
      }
      return left.label.localeCompare(right.label);
    });
  }, [providers]);
  const readyCount = sortedProviders.filter(
    (provider) => provider.detected && provider.missing_env_vars.length === 0,
  ).length;
  const missingSetupCount = sortedProviders.filter(
    (provider) => !provider.detected || provider.missing_env_vars.length > 0,
  ).length;
  const recommendedProvider =
    sortedProviders.find((provider) => provider.detected && provider.missing_env_vars.length === 0) ??
    sortedProviders[0] ??
    null;

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <p className="panel-eyebrow">Providers</p>
          <h2>Setup readiness and desktop preferences</h2>
        </div>
      </div>

      <div className="provider-list">
        {statusMessage ? <section className="status-banner">{statusMessage}</section> : null}
        <div className="provider-summary-strip">
          <SummaryItem label="Providers" value={String(sortedProviders.length)} />
          <SummaryItem label="Ready" value={String(readyCount)} />
          <SummaryItem label="Need setup" value={String(missingSetupCount)} />
          <SummaryItem label="Recommended" value={recommendedProvider?.label || "-"} />
        </div>
        {sortedProviders.map((provider) => (
          <div key={provider.provider_id} className="provider-card">
            <div className="provider-title-row">
              <div>
                <h3>{provider.label}</h3>
                {provider.preferred ? <p className="provider-preferred">Preferred desktop provider</p> : null}
              </div>
              <span className={`pill ${provider.detected ? "pill-good" : "pill-bad"}`}>
                {provider.detected ? "Detected" : "Missing"}
              </span>
            </div>
            <p>{provider.auth_ok ? "Authentication ready" : provider.reason || "Needs setup"}</p>
            <div className="summary-row">
              <SummaryItem
                label="Ready"
                value={provider.detected && provider.missing_env_vars.length === 0 ? "yes" : "not yet"}
              />
              <SummaryItem
                label="Configured"
                value={
                  provider.required_env_vars.length > 0
                    ? `${provider.configured_env_vars.length}/${provider.required_env_vars.length}`
                    : "n/a"
                }
              />
              <SummaryItem label="Binary" value={provider.binary_path ? "found" : "missing"} />
              <SummaryItem label="Preferred" value={provider.preferred ? "yes" : "no"} />
            </div>
            {provider.missing_env_vars.length > 0 ? (
              <p className="provider-meta">Missing env: {provider.missing_env_vars.join(", ")}</p>
            ) : null}
            {provider.required_env_vars.length > 0 ? (
              <div className="provider-config-list">
                {provider.required_env_vars.map((envName) => (
                  <label key={envName} className="provider-field">
                    <span>{envName}</span>
                    <input
                      type="password"
                      value={providerDrafts[provider.provider_id]?.[envName] ?? ""}
                      placeholder={`Enter ${envName}`}
                      onChange={(event) =>
                        setProviderDrafts((current) => ({
                          ...current,
                          [provider.provider_id]: {
                            ...(current[provider.provider_id] || {}),
                            [envName]: event.target.value,
                          },
                        }))
                      }
                    />
                  </label>
                ))}
              </div>
            ) : null}
            {provider.install_commands.length > 0 ? (
              <div className="provider-command-list">
                {provider.install_commands.slice(0, 2).map((command) => (
                  <code key={command}>{command}</code>
                ))}
              </div>
            ) : null}
            {lastInstallResult?.provider_id === provider.provider_id ? (
              <div className={`install-result-card ${lastInstallResult.success ? "install-result-good" : "install-result-bad"}`}>
                <strong>{lastInstallResult.summary}</strong>
                <p>{lastInstallResult.command}</p>
                {lastInstallResult.next_steps.length > 0 ? (
                  <div className="provider-command-list">
                    {lastInstallResult.next_steps.map((step) => (
                      <code key={step}>{step}</code>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
            <div className="provider-actions">
              <button
                type="button"
                className="action-button"
                onClick={() => void installProviderDependency(provider.provider_id)}
                disabled={installingProviderId === provider.provider_id}
              >
                {installingProviderId === provider.provider_id ? "Installing..." : "Install dependency"}
              </button>
              <button type="button" className="action-button" onClick={() => void saveProviderConfig(provider.provider_id, false)}>
                Save values
              </button>
              <button type="button" className="action-button action-button-accent" onClick={() => void saveProviderConfig(provider.provider_id, true)}>
                Make preferred
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

type SetupWorkspaceProps = {
  statusMessage: string;
  setupChecks: DesktopSetupCheck[];
  refreshSetup: () => Promise<void>;
  installSetupDependency: (checkId: string) => Promise<DesktopSetupInstallResult | null>;
  installingSetupCheckId: string;
  lastSetupInstallResult: DesktopSetupInstallResult | null;
  setActiveView: (view: "providers" | "run" | "setup") => void;
};

export function SetupWorkspace(props: SetupWorkspaceProps) {
  const {
    statusMessage,
    setupChecks,
    refreshSetup,
    installSetupDependency,
    installingSetupCheckId,
    lastSetupInstallResult,
    setActiveView,
  } = props;
  const requiredIssues = setupChecks.filter((check) => check.required && !check.detected);
  const optionalIssues = setupChecks.filter((check) => !check.required && !check.detected);
  const readyChecks = setupChecks.filter((check) => check.detected);
  const recommendedAction =
    requiredIssues.length > 0
      ? "Resolve required blockers first before relying on desktop runs."
      : optionalIssues.length > 0
        ? "Desktop runs can work now. Optional tooling only blocks native packaging and advanced workflows."
        : "This machine looks ready for both desktop workflows and future packaging work.";
  const nextGuide =
    requiredIssues[0] ?? optionalIssues[0] ?? null;
  const installRecovered =
    lastSetupInstallResult?.success &&
    !setupChecks.some((check) => check.check_id === lastSetupInstallResult.check_id && !check.detected);

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <p className="panel-eyebrow">Setup</p>
          <h2>Local desktop readiness</h2>
        </div>
      </div>
      {statusMessage ? <section className="status-banner">{statusMessage}</section> : null}
      <div className="provider-summary-strip">
        <SummaryItem label="Checks" value={String(setupChecks.length)} />
        <SummaryItem label="Required blockers" value={String(requiredIssues.length)} />
        <SummaryItem label="Optional gaps" value={String(optionalIssues.length)} />
        <SummaryItem label="Ready" value={requiredIssues.length === 0 ? "yes" : "not yet"} />
      </div>
      <div className="install-result-card">
        <strong>Recommended next action</strong>
        <p>{recommendedAction}</p>
        {nextGuide ? (
          <div className="setup-inline-actions">
            <button
              type="button"
              className="action-button"
              onClick={() => void copyText(nextGuide.install_commands[0] || nextGuide.install_hint)}
            >
              Copy next command
            </button>
            {setupGuideUrls[nextGuide.check_id] ? (
              <button
                type="button"
                className="action-button"
                onClick={() => window.open(setupGuideUrls[nextGuide.check_id], "_blank", "noopener,noreferrer")}
              >
                Open install guide
              </button>
            ) : null}
          </div>
        ) : null}
        {installRecovered ? (
          <div className="setup-followup-strip">
            <span className="pill pill-good">Installed</span>
            <p>
              {lastSetupInstallResult?.check_id} now looks available. If provider setup is complete, the next best step is to return to Run.
            </p>
            <div className="provider-actions compact-actions">
              <button
                type="button"
                className="action-button"
                onClick={() => setActiveView("providers")}
              >
                Review providers
              </button>
              <button
                type="button"
                className="action-button action-button-accent"
                onClick={() => setActiveView("run")}
              >
                Continue to run
              </button>
            </div>
          </div>
        ) : null}
      </div>
      <div className="provider-actions">
        <button type="button" className="action-button" onClick={() => void refreshSetup()}>
          Refresh checks
        </button>
        <button type="button" className="action-button" onClick={() => setActiveView("providers")}>
          Open provider setup
        </button>
        <button type="button" className="action-button action-button-accent" onClick={() => setActiveView("run")}>
          Open run workspace
        </button>
      </div>
      {requiredIssues.length > 0 ? (
        <>
          <div className="panel-head">
            <div>
              <p className="panel-eyebrow">Required</p>
              <h2>Fix these before relying on the local app</h2>
            </div>
          </div>
          <div className="project-list-grid">
            {requiredIssues.map((check) => (
              <article key={check.check_id} className="project-list-card">
                <div className="run-top">
                  <div>
                    <p className="panel-eyebrow">Dependency</p>
                    <h3>{check.label}</h3>
                  </div>
                  <span className="pill pill-bad">Required</span>
                </div>
                <div className="summary-row">
                  <SummaryItem label="Version" value={check.version || "-"} />
                  <SummaryItem label="Detected" value={check.detected ? "yes" : "no"} />
                  <SummaryItem label="Required" value="yes" />
                  <SummaryItem label="Id" value={check.check_id} />
                </div>
                <p>{check.reason || check.install_hint}</p>
                <div className="provider-command-list">
                  <code>{check.install_hint}</code>
                  {check.install_commands.map((command) => (
                    <code key={command}>{command}</code>
                  ))}
                </div>
                {lastSetupInstallResult?.check_id === check.check_id ? (
                  <div
                    className={`install-result-card ${lastSetupInstallResult.success ? "install-result-good" : "install-result-bad"}`}
                  >
                    <strong>{lastSetupInstallResult.summary}</strong>
                    <p>{lastSetupInstallResult.command}</p>
                    {lastSetupInstallResult.next_steps.length > 0 ? (
                      <div className="provider-command-list">
                        {lastSetupInstallResult.next_steps.map((step) => (
                          <code key={step}>{step}</code>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}
                {check.install_commands.length > 0 ? (
                  <div className="provider-actions">
                    <button
                      type="button"
                      className="action-button"
                      onClick={() => void installSetupDependency(check.check_id)}
                      disabled={installingSetupCheckId === check.check_id}
                    >
                      {installingSetupCheckId === check.check_id ? "Installing..." : "Install dependency"}
                    </button>
                    <button
                      type="button"
                      className="action-button"
                      onClick={() => void copyText(check.install_commands[0])}
                    >
                      Copy command
                    </button>
                    {setupGuideUrls[check.check_id] ? (
                      <button
                        type="button"
                        className="action-button"
                        onClick={() => window.open(setupGuideUrls[check.check_id], "_blank", "noopener,noreferrer")}
                      >
                        Open guide
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </>
      ) : null}
      {optionalIssues.length > 0 ? (
        <>
          <div className="panel-head">
            <div>
              <p className="panel-eyebrow">Optional</p>
              <h2>Nice to have for packaging and advanced flows</h2>
            </div>
          </div>
          <div className="project-list-grid">
            {optionalIssues.map((check) => (
              <article key={check.check_id} className="project-list-card">
                <div className="run-top">
                  <div>
                    <p className="panel-eyebrow">Dependency</p>
                    <h3>{check.label}</h3>
                  </div>
                  <span className="pill pill-warn">Optional</span>
                </div>
                <div className="summary-row">
                  <SummaryItem label="Version" value={check.version || "-"} />
                  <SummaryItem label="Detected" value={check.detected ? "yes" : "no"} />
                  <SummaryItem label="Required" value="no" />
                  <SummaryItem label="Id" value={check.check_id} />
                </div>
                <p>{check.reason || check.install_hint}</p>
                <div className="provider-command-list">
                  <code>{check.install_hint}</code>
                  {check.install_commands.map((command) => (
                    <code key={command}>{command}</code>
                  ))}
                </div>
                {lastSetupInstallResult?.check_id === check.check_id ? (
                  <div
                    className={`install-result-card ${lastSetupInstallResult.success ? "install-result-good" : "install-result-bad"}`}
                  >
                    <strong>{lastSetupInstallResult.summary}</strong>
                    <p>{lastSetupInstallResult.command}</p>
                    {lastSetupInstallResult.next_steps.length > 0 ? (
                      <div className="provider-command-list">
                        {lastSetupInstallResult.next_steps.map((step) => (
                          <code key={step}>{step}</code>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}
                {check.install_commands.length > 0 ? (
                  <div className="provider-actions">
                    <button
                      type="button"
                      className="action-button"
                      onClick={() => void installSetupDependency(check.check_id)}
                      disabled={installingSetupCheckId === check.check_id}
                    >
                      {installingSetupCheckId === check.check_id ? "Installing..." : "Install dependency"}
                    </button>
                    <button
                      type="button"
                      className="action-button"
                      onClick={() => void copyText(check.install_commands[0])}
                    >
                      Copy command
                    </button>
                    {setupGuideUrls[check.check_id] ? (
                      <button
                        type="button"
                        className="action-button"
                        onClick={() => window.open(setupGuideUrls[check.check_id], "_blank", "noopener,noreferrer")}
                      >
                        Open guide
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </>
      ) : null}
      {readyChecks.length > 0 ? (
        <div className="project-list-grid">
          {readyChecks.slice(0, 3).map((check) => (
            <article key={check.check_id} className="project-list-card">
              <div className="run-top">
                <div>
                  <p className="panel-eyebrow">Ready</p>
                  <h3>{check.label}</h3>
                </div>
                <span className="pill pill-good">Ready</span>
              </div>
              <div className="summary-row">
                <SummaryItem label="Version" value={check.version || "-"} />
                <SummaryItem label="Detected" value="yes" />
                <SummaryItem label="Required" value={check.required ? "yes" : "no"} />
                <SummaryItem label="Id" value={check.check_id} />
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
