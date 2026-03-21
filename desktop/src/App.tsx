import { useEffect, useMemo, useState } from "react";

import { invokeAppRuntime } from "./bridge";
import type {
  DesktopAppHealth,
  DesktopProjectSummary,
  DesktopProviderStatus,
  WorkflowArtifactDocument,
  WorkflowRunDetail,
  WorkflowRunSummary,
} from "./types";

type LoadState = "idle" | "loading" | "ready" | "error";

const surfaces = ["Projects", "Workflow", "Providers", "Run"];

export function App() {
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
        setSelectedArtifactTitle((current) => current || detail.artifacts.find((artifact) => artifact.exists)?.title || detail.artifacts[0]?.title || "");
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
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save provider config.");
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">AOP Desktop</p>
          <h1>Workflow-first local app for idea to MVP execution.</h1>
          <p className="lede">
            Desktop MVP is now connected to the new Python runtime bridge. This page already reads
            real AOP health, project, provider, and workflow run data.
          </p>
        </div>
        <div className="hero-status">
          <div className="status-panel">
            <span className={`pill ${loadState === "ready" ? "pill-good" : loadState === "error" ? "pill-bad" : "pill-warn"}`}>
              {loadState}
            </span>
            <p className="status-label">Bridge status</p>
            <h2>{health ? `v${health.version}` : "Waiting"}</h2>
            <p className="status-subtle">{health ? `${health.platform} runtime detected` : "Starting local bridge..."}</p>
          </div>
        </div>
      </section>

      {error ? <section className="alert">{error}</section> : null}

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
              <p className="panel-eyebrow">Current scope</p>
              <h2>Desktop MVP surfaces</h2>
            </div>
            <div className="chip-row">
              {surfaces.map((surface) => (
                <span key={surface} className="chip">
                  {surface}
                </span>
              ))}
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
        </article>

        <article className="panel">
          <div className="panel-head">
            <div>
              <p className="panel-eyebrow">Providers</p>
              <h2>Setup readiness</h2>
            </div>
          </div>
          <div className="provider-list">
            {providers.map((provider) => (
              <div key={provider.provider_id} className="provider-card">
                <div className="provider-title-row">
                  <div>
                    <h3>{provider.label}</h3>
                    {provider.preferred ? <p className="provider-preferred">Preferred desktop provider</p> : null}
                  </div>
                  <span className={`pill ${provider.detected ? "pill-good" : "pill-bad"}`}>{provider.detected ? "Detected" : "Missing"}</span>
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
        </article>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <p className="panel-eyebrow">Workflow</p>
            <h2>Recent runs</h2>
          </div>
        </div>
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
    </main>
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
