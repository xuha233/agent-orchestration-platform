import { useEffect, useMemo, useState } from "react";

import { invokeAppRuntime } from "./bridge";
import type {
  DesktopAppHealth,
  DesktopProjectSummary,
  DesktopProviderStatus,
  DesktopRunJob,
  DesktopRunLaunchResult,
  WorkflowArtifactDocument,
  WorkflowRunDetail,
  WorkflowRunSummary,
} from "./types";

type LoadState = "idle" | "loading" | "ready" | "error";
type ViewName = "home" | "projects" | "providers" | "run" | "workflow";

const navItems: Array<{ id: ViewName; label: string; desc: string }> = [
  { id: "home", label: "Home", desc: "Overview and next actions" },
  { id: "projects", label: "Projects", desc: "Register and inspect workspaces" },
  { id: "providers", label: "Providers", desc: "Setup and preferred routing" },
  { id: "run", label: "Run", desc: "Launch a workflow from desktop" },
  { id: "workflow", label: "Workflow", desc: "Inspect persisted run artifacts" },
];

export function App() {
  const [activeView, setActiveView] = useState<ViewName>("home");
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState("");
  const [health, setHealth] = useState<DesktopAppHealth | null>(null);
  const [projects, setProjects] = useState<DesktopProjectSummary[]>([]);
  const [providers, setProviders] = useState<DesktopProviderStatus[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [runs, setRuns] = useState<WorkflowRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [runDetail, setRunDetail] = useState<WorkflowRunDetail | null>(null);
  const [selectedArtifactTitle, setSelectedArtifactTitle] = useState("");
  const [providerDrafts, setProviderDrafts] = useState<Record<string, Record<string, string>>>({});
  const [runPrompt, setRunPrompt] = useState("");
  const [runSubmitting, setRunSubmitting] = useState(false);
  const [runJob, setRunJob] = useState<DesktopRunJob | null>(null);
  const [runResult, setRunResult] = useState<DesktopRunLaunchResult | null>(null);
  const [projectNameDraft, setProjectNameDraft] = useState("");
  const [projectPathDraft, setProjectPathDraft] = useState("");
  const [projectAgentDraft, setProjectAgentDraft] = useState("codex");
  const [projectSubmitting, setProjectSubmitting] = useState(false);
  const [workflowRefreshing, setWorkflowRefreshing] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [jobPollCount, setJobPollCount] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoadState("loading");
      setError("");
      try {
        const [healthData, projectData, providerData] = await Promise.all([
          invokeAppRuntime<DesktopAppHealth>("health"),
          invokeAppRuntime<DesktopProjectSummary[]>("projects"),
          invokeAppRuntime<DesktopProviderStatus[]>("providers"),
        ]);
        if (cancelled) {
          return;
        }
        setHealth(healthData);
        setProjects(projectData);
        setProviders(providerData);
        setProviderDrafts(
          Object.fromEntries(
            providerData.map((provider) => [provider.provider_id, provider.stored_env_vars || {}]),
          ),
        );
        setSelectedProjectId((current) => current || projectData[0]?.project_id || "");
        setLoadState("ready");
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Failed to load desktop bridge data.");
        setLoadState("error");
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!runJob || (runJob.status !== "queued" && runJob.status !== "running")) {
      return;
    }
    const activeJob: DesktopRunJob = runJob;

    async function pollJob() {
      try {
        const nextJob = await invokeAppRuntime<DesktopRunJob>("run_job_status", {
          job_id: activeJob.job_id,
        });
        if (cancelled) {
          return;
        }
        setJobPollCount((current) => current + 1);
        setRunJob(nextJob);
        await refreshProjectData(nextJob.project_id);
        if (nextJob.sprint_id) {
          await refreshWorkflowRuns(nextJob.sprint_id, nextJob.project_id);
        } else if (nextJob.status === "running") {
          await refreshWorkflowRuns(undefined, nextJob.project_id);
        }
        if (nextJob.status === "completed" || nextJob.status === "failed") {
          const result: DesktopRunLaunchResult | null = nextJob.sprint_id
            ? {
                project_id: nextJob.project_id,
                sprint_id: nextJob.sprint_id,
                success: nextJob.status === "completed",
                state: nextJob.state || nextJob.status,
                summary:
                  nextJob.summary ||
                  (nextJob.status === "completed"
                    ? "Desktop run completed."
                    : "Desktop run finished with issues."),
                next_steps: nextJob.next_steps,
              }
            : null;
          setRunResult(result);
          setStatusMessage(
            nextJob.status === "completed"
              ? `Run ${nextJob.sprint_id} completed. Review workflow artifacts for the full trace.`
              : nextJob.error
                ? formatRuntimeError(nextJob.error)
                : "Desktop run stopped before completion. Review workflow details for follow-up.",
          );
          if (nextJob.sprint_id && activeView === "run") {
            setActiveView("workflow");
          }
          return;
        }
      } catch (pollError) {
        if (!cancelled) {
          setError(
            pollError instanceof Error ? pollError.message : "Failed to poll desktop run job.",
          );
        }
      }
      if (!cancelled) {
        window.setTimeout(() => {
          void pollJob();
        }, 2000);
      }
    }

    void pollJob();
    return () => {
      cancelled = true;
    };
  }, [runJob?.job_id, runJob?.status]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedProjectId) {
      setRuns([]);
      setSelectedRunId("");
      setRunDetail(null);
      setSelectedArtifactTitle("");
      return;
    }

    async function loadRuns() {
      try {
        const runData = await invokeAppRuntime<WorkflowRunSummary[]>("runs", {
          project_id: selectedProjectId,
          limit: 6,
        });
        if (!cancelled) {
          setRuns(runData);
          setSelectedRunId((current) =>
            current && runData.some((run) => run.run_id === current) ? current : runData[0]?.run_id || "",
          );
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load workflow runs.");
        }
      }
    }

    void loadRuns();
    return () => {
      cancelled = true;
    };
  }, [selectedProjectId]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedProjectId || !selectedRunId) {
      setRunDetail(null);
      setSelectedArtifactTitle("");
      return;
    }

    async function loadRunDetail() {
      try {
        const detail = await invokeAppRuntime<WorkflowRunDetail>("run_detail", {
          project_id: selectedProjectId,
          run_id: selectedRunId,
        });
        if (cancelled) {
          return;
        }
        setRunDetail(detail);
        setSelectedArtifactTitle(
          (current) =>
            (current && detail.artifacts.some((artifact) => artifact.title === current)
              ? current
              :
            detail.artifacts.find((artifact) => artifact.exists)?.title ||
            detail.artifacts[0]?.title) ||
            "",
        );
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load workflow run detail.");
        }
      }
    }

    void loadRunDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedProjectId, selectedRunId]);

  const selectedProject = useMemo(
    () => projects.find((project) => project.project_id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );
  const selectedArtifact = useMemo(
    () => runDetail?.artifacts.find((artifact) => artifact.title === selectedArtifactTitle) ?? null,
    [runDetail, selectedArtifactTitle],
  );
  const preferredProvider = useMemo(
    () => providers.find((provider) => provider.preferred) ?? null,
    [providers],
  );
  const followUpProjects = useMemo(
    () => projects.filter((project) => project.needs_follow_up),
    [projects],
  );
  const activeNav = navItems.find((item) => item.id === activeView);
  const runInFlight = Boolean(runJob && (runJob.status === "queued" || runJob.status === "running"));
  const activeRunSummary = useMemo(() => {
    if (!runJob?.sprint_id) {
      return null;
    }
    return runs.find((run) => run.run_id === runJob.sprint_id) ?? null;
  }, [runJob?.sprint_id, runs]);

  const runBlockerMessage = useMemo(() => {
    if (!selectedProjectId) {
      return "Choose a project before starting a desktop run.";
    }
    if (!preferredProvider) {
      return "Pick a preferred provider first so the desktop runtime knows what to use.";
    }
    if (preferredProvider.missing_env_vars.length > 0) {
      return `Preferred provider ${preferredProvider.label} is still missing ${preferredProvider.missing_env_vars.join(", ")}.`;
    }
    if (!preferredProvider.detected) {
      return `Preferred provider ${preferredProvider.label} is not detected on this machine yet.`;
    }
    return "";
  }, [preferredProvider, selectedProjectId]);

  function formatRuntimeError(message: string): string {
    if (message.startsWith("preferred_provider_missing_env:")) {
      const [, providerId, missing] = message.split(":");
      return `Preferred provider ${providerId} still needs ${missing} before desktop runs can start.`;
    }
    if (message.startsWith("preferred_provider_unavailable:")) {
      const [, providerId] = message.split(":");
      return `Preferred provider ${providerId} is not available on this machine yet.`;
    }
    if (message.startsWith("project_path_missing:")) {
      return "The selected project path no longer exists. Update or re-register the workspace.";
    }
    if (message.startsWith("workspace_not_found:")) {
      return "The selected workspace could not be found. Refresh projects and try again.";
    }
    if (message === "prompt_required") {
      return "Enter a prompt before starting a desktop run.";
    }
    return message;
  }

  async function refreshProjectData(nextProjectId?: string) {
    const [projectData, providerData] = await Promise.all([
      invokeAppRuntime<DesktopProjectSummary[]>("projects"),
      invokeAppRuntime<DesktopProviderStatus[]>("providers"),
    ]);
    setProjects(projectData);
    setProviders(providerData);
    setProviderDrafts(
      Object.fromEntries(
        providerData.map((provider) => [provider.provider_id, provider.stored_env_vars || {}]),
      ),
    );
    if (nextProjectId) {
      setSelectedProjectId(nextProjectId);
    }
  }

  async function refreshWorkflowRuns(nextRunId?: string, projectIdOverride?: string) {
    const projectId = projectIdOverride || selectedProjectId;
    if (!projectId) {
      return;
    }
    setWorkflowRefreshing(true);
    try {
      const runData = await invokeAppRuntime<WorkflowRunSummary[]>("runs", {
        project_id: projectId,
        limit: 6,
      });
      setRuns(runData);
      if (projectIdOverride) {
        setSelectedProjectId(projectIdOverride);
      }
      if (nextRunId) {
        setSelectedRunId(nextRunId);
      } else if (!runData.find((run) => run.run_id === selectedRunId)) {
        setSelectedRunId(runData[0]?.run_id || "");
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to refresh workflow runs.");
    } finally {
      setWorkflowRefreshing(false);
    }
  }

  async function saveProviderConfig(providerId: string, preferred: boolean) {
    try {
      const updated = await invokeAppRuntime<DesktopProviderStatus>("update_provider", {
        provider_id: providerId,
        env_values: providerDrafts[providerId] || {},
        preferred,
      });
      setProviders((current) =>
        current.map((provider) => {
          if (provider.provider_id === updated.provider_id) {
            return updated;
          }
          if (preferred) {
            return { ...provider, preferred: false };
          }
          return provider;
        }),
      );
      setProviderDrafts((current) => ({
        ...current,
        [providerId]: updated.stored_env_vars,
      }));
      setStatusMessage(
        preferred
          ? `${updated.label} is now the preferred desktop provider.`
          : `${updated.label} values saved for desktop runtime use.`,
      );
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save provider config.");
    }
  }

  async function submitRun() {
    if (!selectedProjectId || !runPrompt.trim()) {
      setError("Please choose a project and enter a run prompt.");
      return;
    }
    setRunSubmitting(true);
    setError("");
    try {
      const job = await invokeAppRuntime<DesktopRunJob>("start_run_async", {
        project_id: selectedProjectId,
        prompt: runPrompt,
      });
      setJobPollCount(0);
      setRunJob(job);
      setRunResult(null);
      setRunPrompt("");
      setStatusMessage(
        "Desktop run queued. AOP will keep polling until workflow artifacts are ready.",
      );
    } catch (submitError) {
      setError(
        formatRuntimeError(
          submitError instanceof Error ? submitError.message : "Failed to start desktop run.",
        ),
      );
    } finally {
      setRunSubmitting(false);
    }
  }

  async function createProject() {
    if (!projectPathDraft.trim()) {
      setError("Please enter a project path to register.");
      return;
    }
    setProjectSubmitting(true);
    setError("");
    try {
      const project = await invokeAppRuntime<DesktopProjectSummary>("create_project", {
        project_name: projectNameDraft,
        project_path: projectPathDraft,
        primary_agent: projectAgentDraft,
      });
      setProjectNameDraft("");
      setProjectPathDraft("");
      setActiveView("projects");
      await refreshProjectData(project.project_id);
      setStatusMessage(`${project.name} is now registered and ready for desktop workflows.`);
    } catch (createError) {
      setError(
        formatRuntimeError(
          createError instanceof Error ? createError.message : "Failed to register desktop project.",
        ),
      );
    } finally {
      setProjectSubmitting(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="sidebar-brand">
          <p className="eyebrow">AOP Desktop</p>
          <h1>Workflow-first local app</h1>
          <p>{activeNav?.desc || "Desktop MVP shell"}</p>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-button ${activeView === item.id ? "nav-button-active" : ""}`}
              onClick={() => setActiveView(item.id)}
            >
              <strong>{item.label}</strong>
              <span>{item.desc}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className={`pill ${loadState === "ready" ? "pill-good" : loadState === "error" ? "pill-bad" : "pill-warn"}`}>
            {loadState}
          </span>
          <p>{health ? `v${health.version} on ${health.platform}` : "Waiting for runtime bridge"}</p>
        </div>
      </aside>

      <main className="shell shell-main">
        {activeView === "home" ? (
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
              <MetricCard label="Runs" value={String(runs.length)} />
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
                      <code key={project.project_id}>{project.name} — {project.latest_run_phase || "no phase"}</code>
                    ))}
                  </div>
                ) : (
                  <EmptyState title="Queue is clear" body="No projects currently need follow-up from the latest workflow run." />
                )}
              </article>
            </section>
          </>
        ) : null}

        {activeView === "projects" ? (
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
              </div>
            ) : (
              <EmptyState title="No project selected" body="Create or register a workspace to see desktop project summaries here." />
            )}
          </section>
        ) : null}

        {activeView === "providers" ? (
          <section className="panel">
            <div className="panel-head">
              <div>
                <p className="panel-eyebrow">Providers</p>
                <h2>Setup readiness and desktop preferences</h2>
              </div>
            </div>

            <div className="provider-list">
              {statusMessage ? <section className="status-banner">{statusMessage}</section> : null}
              {providers.map((provider) => (
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
                  <div className="provider-actions">
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
        ) : null}

        {activeView === "run" ? (
          <section className="panel">
            <div className="panel-head">
              <div>
                <p className="panel-eyebrow">Run</p>
                <h2>Start a workflow from desktop</h2>
              </div>
            </div>
            <div className="run-composer">
              {statusMessage ? <section className="status-banner">{statusMessage}</section> : null}
              {runInFlight ? (
                <div className="live-run-banner">
                  <div>
                    <p className="panel-eyebrow">Live run monitor</p>
                    <h3>{runJob?.status === "queued" ? "Preparing desktop worker" : "Workflow running"}</h3>
                    <p>
                      {runJob?.status === "queued"
                        ? "The background worker is being started. AOP will start refreshing workflow data as soon as the run appears."
                        : "AOP is polling the local worker, refreshing project state, and tracking new workflow artifacts for you."}
                    </p>
                  </div>
                  <div className="summary-row">
                    <SummaryItem label="Polls" value={String(jobPollCount)} />
                    <SummaryItem label="Job" value={runJob?.job_id.slice(0, 12) || "-"} />
                    <SummaryItem label="State" value={runJob?.state || runJob?.status || "-"} />
                    <SummaryItem label="Live run" value={runJob?.sprint_id || activeRunSummary?.run_id || "Waiting"} />
                  </div>
                  <div className="provider-actions">
                    <button
                      type="button"
                      className="action-button"
                      onClick={() => setActiveView("workflow")}
                    >
                      Watch workflow
                    </button>
                    <button
                      type="button"
                      className="action-button"
                      onClick={() => void refreshWorkflowRuns(runJob?.sprint_id || undefined, selectedProjectId)}
                      disabled={workflowRefreshing}
                    >
                      {workflowRefreshing ? "Refreshing..." : "Refresh now"}
                    </button>
                  </div>
                </div>
              ) : null}
              <label htmlFor="run-prompt">What should AOP build or validate?</label>
              <textarea
                id="run-prompt"
                value={runPrompt}
                onChange={(event) => setRunPrompt(event.target.value)}
                placeholder="Describe the idea, feature, or prototype you want AOP to work on."
              />
              {runBlockerMessage ? <div className="inline-note">{runBlockerMessage}</div> : null}
              <div className="provider-actions">
                <button
                  type="button"
                  className="action-button action-button-accent"
                  onClick={() => void submitRun()}
                  disabled={runSubmitting || Boolean(runBlockerMessage)}
                >
                  {runSubmitting ? "Running..." : "Start run"}
                </button>
                {runJob?.sprint_id ? (
                  <button
                    type="button"
                    className="action-button"
                    onClick={() => setActiveView("workflow")}
                  >
                    Open workflow
                  </button>
                ) : null}
              </div>
              {runJob && !runResult ? (
                <div className="run-result-card">
                  <div className="run-top">
                    <div>
                      <h3>{runJob.job_id}</h3>
                      <p>
                        {runJob.status === "queued"
                          ? "Queued and waiting for the desktop worker to start."
                          : runJob.status === "running"
                            ? "Running now. Workflow runs and artifacts will refresh automatically when it finishes."
                            : runJob.summary || runJob.error || "Desktop run finished."}
                      </p>
                    </div>
                    <span
                      className={`pill ${
                        runJob.status === "completed"
                          ? "pill-good"
                          : runJob.status === "failed"
                            ? "pill-bad"
                            : "pill-warn"
                      }`}
                    >
                      {runJob.status}
                    </span>
                  </div>
                  <div className="summary-row">
                    <SummaryItem label="Project" value={selectedProject?.name || runJob.project_id} />
                    <SummaryItem label="Sprint" value={runJob.sprint_id || "-"} />
                    <SummaryItem label="State" value={runJob.state || "-"} />
                    <SummaryItem label="Updated" value={runJob.updated_at.replace("T", " ").slice(0, 19)} />
                  </div>
                  {runJob.next_steps.length > 0 ? (
                    <div className="provider-command-list">
                      {runJob.next_steps.map((step) => (
                        <code key={step}>{step}</code>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
              {runResult ? (
                <div className="run-result-card">
                  <div className="run-top">
                    <div>
                      <h3>{runResult.sprint_id}</h3>
                      <p>{runResult.summary}</p>
                    </div>
                    <span className={`pill ${runResult.success ? "pill-good" : "pill-warn"}`}>{runResult.state}</span>
                  </div>
                  {runResult.next_steps.length > 0 ? (
                    <div className="provider-command-list">
                      {runResult.next_steps.map((step) => (
                        <code key={step}>{step}</code>
                      ))}
                    </div>
                  ) : null}
                  <div className="provider-actions">
                    <button type="button" className="action-button" onClick={() => setActiveView("workflow")}>
                      Open workflow details
                    </button>
                    <button type="button" className="action-button" onClick={() => setActiveView("providers")}>
                      Review provider setup
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          </section>
        ) : null}

        {activeView === "workflow" ? (
          <section className="panel">
            <div className="panel-head">
              <div>
                <p className="panel-eyebrow">Workflow</p>
                <h2>Recent runs and artifact details</h2>
              </div>
              <div className="provider-actions compact-actions">
                <button
                  type="button"
                  className="action-button"
                  onClick={() => void refreshWorkflowRuns()}
                  disabled={workflowRefreshing || !selectedProjectId}
                >
                  {workflowRefreshing ? "Refreshing..." : "Refresh runs"}
                </button>
              </div>
            </div>
            {statusMessage ? <section className="status-banner">{statusMessage}</section> : null}
            {runInFlight ? (
              <section className="workflow-live-strip">
                <div>
                  <p className="panel-eyebrow">Live sync</p>
                  <h3>{runJob?.status === "queued" ? "Waiting for run to appear" : "Tracking active workflow"}</h3>
                  <p>
                    {runJob?.sprint_id
                      ? `Focused on ${runJob.sprint_id}. Runs refresh automatically while the desktop worker is active.`
                      : "The desktop worker is active. This view will refresh runs automatically as soon as workflow artifacts land."}
                  </p>
                </div>
                <div className="summary-row">
                  <SummaryItem label="Job" value={runJob?.job_id.slice(0, 10) || "-"} />
                  <SummaryItem label="Status" value={runJob?.status || "-"} />
                  <SummaryItem label="State" value={runJob?.state || "-"} />
                  <SummaryItem label="Polls" value={String(jobPollCount)} />
                </div>
              </section>
            ) : null}
            {runs.length === 0 ? (
              <EmptyState title="No workflow runs yet" body="Once a project starts producing workflow artifacts, runs will show up here." />
            ) : (
              <div className="workflow-layout">
                <div className="run-list">
                  {runs.map((run) => (
                    <button
                      key={run.run_id}
                      type="button"
                      className={`run-card run-button ${selectedRunId === run.run_id ? "run-card-active" : ""}`}
                      onClick={() => setSelectedRunId(run.run_id)}
                    >
                      <div className="run-top">
                        <div>
                          <h3>{run.run_id}</h3>
                          <p>{run.clarified_summary || run.original_input || "No summary available."}</p>
                        </div>
                        <span className={`pill ${run.status === "completed" ? "pill-good" : "pill-warn"}`}>{run.status}</span>
                      </div>
                      <div className="summary-row">
                        <SummaryItem label="Phase" value={run.current_phase || "-"} />
                        <SummaryItem label="Verify" value={run.verification_verdict || "-"} />
                        <SummaryItem label="Completion" value={run.completion_status || "-"} />
                        <SummaryItem label="Flags" value={run.has_gaps || run.has_guardrails ? "attention" : "stable"} />
                      </div>
                    </button>
                  ))}
                </div>

                <div className="artifact-panel">
                  {runDetail ? (
                    <>
                      <div className="panel-head">
                        <div>
                          <p className="panel-eyebrow">Artifact detail</p>
                          <h2>{runDetail.summary.run_id}</h2>
                        </div>
                        <span className={`pill ${runDetail.summary.status === "completed" ? "pill-good" : "pill-warn"}`}>
                          {runDetail.summary.status}
                        </span>
                      </div>

                      <div className="summary-row">
                        <SummaryItem label="Phase" value={runDetail.summary.current_phase || "-"} />
                        <SummaryItem label="Verify" value={runDetail.summary.verification_verdict || "-"} />
                        <SummaryItem label="Completion" value={runDetail.summary.completion_status || "-"} />
                        <SummaryItem label="Artifacts" value={String(runDetail.artifacts.filter((artifact) => artifact.exists).length)} />
                      </div>

                      <div className="artifact-toolbar">
                        <label htmlFor="artifact-select">Focused artifact</label>
                        <select
                          id="artifact-select"
                          value={selectedArtifactTitle}
                          onChange={(event) => setSelectedArtifactTitle(event.target.value)}
                        >
                          {runDetail.artifacts.map((artifact) => (
                            <option key={artifact.title} value={artifact.title}>
                              {artifact.title}
                            </option>
                          ))}
                        </select>
                      </div>

                      {selectedArtifact ? (
                        <ArtifactViewer artifact={selectedArtifact} />
                      ) : (
                        <EmptyState title="No artifact selected" body="Choose an artifact to inspect its contents." />
                      )}
                    </>
                  ) : (
                    <EmptyState title="No run detail loaded" body="Choose a workflow run to inspect persisted artifacts." />
                  )}
                </div>
              </div>
            )}
          </section>
        ) : null}
      </main>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="metric-card">
      <p>{label}</p>
      <strong>{value}</strong>
    </article>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="summary-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}

function ArtifactViewer({ artifact }: { artifact: WorkflowArtifactDocument }) {
  const metadataEntries = Object.entries(artifact.metadata || {}).filter(([, value]) => {
    if (Array.isArray(value)) {
      return value.length > 0;
    }
    return value !== "" && value !== null && value !== undefined;
  });

  return (
    <div className="artifact-viewer">
      <div className="artifact-heading">
        <div>
          <p className="panel-eyebrow">Artifact file</p>
          <h3>{artifact.filename}</h3>
        </div>
        <span className={`pill ${artifact.exists ? "pill-good" : "pill-warn"}`}>
          {artifact.exists ? "Available" : "Missing"}
        </span>
      </div>

      {metadataEntries.length > 0 ? (
        <div className="artifact-metadata">
          {metadataEntries.slice(0, 6).map(([key, value]) => (
            <SummaryItem
              key={key}
              label={key.split("_").join(" ")}
              value={Array.isArray(value) ? String(value.length) : String(value)}
            />
          ))}
        </div>
      ) : null}

      <pre className="artifact-content">{artifact.content || "No artifact content available."}</pre>
    </div>
  );
}
