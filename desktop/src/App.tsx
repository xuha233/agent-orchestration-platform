import { useEffect, useMemo, useState } from "react";

import { invokeAppRuntime } from "./bridge";
import type {
  DesktopAppHealth,
  DesktopProjectSummary,
  DesktopProviderStatus,
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
  const [runResult, setRunResult] = useState<DesktopRunLaunchResult | null>(null);
  const [projectNameDraft, setProjectNameDraft] = useState("");
  const [projectPathDraft, setProjectPathDraft] = useState("");
  const [projectAgentDraft, setProjectAgentDraft] = useState("codex");
  const [projectSubmitting, setProjectSubmitting] = useState(false);
  const [workflowRefreshing, setWorkflowRefreshing] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");

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
    if (!selectedProjectId) {
      setRuns([]);
      setSelectedRunId("");
      setRunDetail(null);
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
          setSelectedRunId((current) => current || runData[0]?.run_id || "");
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
            current ||
            detail.artifacts.find((artifact) => artifact.exists)?.title ||
            detail.artifacts[0]?.title ||
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

  async function refreshWorkflowRuns(nextRunId?: string) {
    if (!selectedProjectId) {
      return;
    }
    setWorkflowRefreshing(true);
    try {
      const runData = await invokeAppRuntime<WorkflowRunSummary[]>("runs", {
        project_id: selectedProjectId,
        limit: 6,
      });
      setRuns(runData);
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
      const result = await invokeAppRuntime<DesktopRunLaunchResult>("start_run", {
        project_id: selectedProjectId,
        prompt: runPrompt,
      });
      setRunResult(result);
      setRunPrompt("");
      setActiveView("workflow");
      setStatusMessage(
        result.success
          ? `Run ${result.sprint_id} completed. Review artifacts and next steps.`
          : `Run ${result.sprint_id} finished with issues. Open workflow details to inspect the outcome.`,
      );
      await refreshProjectData(selectedProjectId);
      await refreshWorkflowRuns(result.sprint_id);
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
              </div>
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
