import { useEffect, useMemo, useState } from "react";

import { invokeAppRuntime } from "./bridge";
import type {
  DesktopAppHealth,
  DesktopInstallResult,
  DesktopProjectSummary,
  DesktopProviderStatus,
  DesktopRunJob,
  DesktopRunLaunchResult,
  WorkflowRunDetail,
  WorkflowRunSummary,
} from "./types";
import { HomeWorkspace, ProjectsWorkspace, ProvidersWorkspace } from "./shell_views";
import { RunWorkspace, WorkflowWorkspace } from "./workflow_views";

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
  const [installingProviderId, setInstallingProviderId] = useState("");
  const [lastInstallResult, setLastInstallResult] = useState<DesktopInstallResult | null>(null);

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
  const preferredProvider = useMemo(
    () => providers.find((provider) => provider.preferred) ?? null,
    [providers],
  );
  const followUpProjects = useMemo(
    () => projects.filter((project) => project.needs_follow_up),
    [projects],
  );
  const prioritizedProjects = useMemo(() => {
    return [...projects].sort((left, right) => {
      if (left.needs_follow_up !== right.needs_follow_up) {
        return left.needs_follow_up ? -1 : 1;
      }
      if (left.latest_run_status !== right.latest_run_status) {
        if (left.latest_run_status !== "completed") {
          return -1;
        }
        if (right.latest_run_status !== "completed") {
          return 1;
        }
      }
      return (right.last_active || "").localeCompare(left.last_active || "");
    });
  }, [projects]);
  const activeNav = navItems.find((item) => item.id === activeView);
  const runInFlight = Boolean(runJob && (runJob.status === "queued" || runJob.status === "running"));
  const activeRunSummary = useMemo(() => {
    if (!runJob?.sprint_id) {
      return null;
    }
    return runs.find((run) => run.run_id === runJob.sprint_id) ?? null;
  }, [runJob?.sprint_id, runs]);
  const trackedRunDetail = useMemo(() => {
    if (!runJob?.sprint_id || !runDetail || runDetail.summary.run_id !== runJob.sprint_id) {
      return null;
    }
    return runDetail;
  }, [runDetail, runJob?.sprint_id]);
  const trackedArtifacts = useMemo(
    () => trackedRunDetail?.artifacts.filter((artifact) => artifact.exists) ?? [],
    [trackedRunDetail],
  );
  const runGuidance = useMemo(() => {
    if (runJob?.status === "queued") {
      return {
        title: "Preparing worker",
        body: "The desktop sidecar is starting. Stay here for live status or jump to Workflow once the run id appears.",
      };
    }
    if (activeRunSummary?.has_guardrails) {
      return {
        title: "Needs workflow review",
        body: "Guardrails were triggered for the active run. Open workflow details and inspect guardrail or completion artifacts first.",
      };
    }
    if (activeRunSummary?.has_gaps) {
      return {
        title: "Gap closure likely",
        body: "Verification gaps are present. Check verification and gaps artifacts to see what still needs to be repaired.",
      };
    }
    if (runJob?.status === "running") {
      return {
        title: "Artifacts are landing",
        body: "AOP is actively refreshing run data. As soon as PLAN or EXECUTION artifacts appear, you can inspect them from the workflow page.",
      };
    }
    if (runResult?.success) {
      return {
        title: "Review the final trace",
        body: "The run finished successfully. The next best step is to inspect completion and summary artifacts before starting another workflow.",
      };
    }
    return {
      title: "Ready for the next run",
      body: "Use this page to launch a workflow, then watch the active run and its artifacts from a single place.",
    };
  }, [activeRunSummary?.has_gaps, activeRunSummary?.has_guardrails, runJob?.status, runResult?.success]);

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

  async function installProviderDependency(providerId: string) {
    setInstallingProviderId(providerId);
    setError("");
    try {
      const result = await invokeAppRuntime<DesktopInstallResult>("install_provider", {
        provider_id: providerId,
      });
      setLastInstallResult(result);
      setStatusMessage(result.summary);
      await refreshProjectData();
      return result;
    } catch (installError) {
      setError(
        installError instanceof Error ? installError.message : "Failed to install provider dependency.",
      );
      return null;
    } finally {
      setInstallingProviderId("");
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

  function focusProject(projectId: string, nextView: "projects" | "run" | "workflow") {
    setSelectedProjectId(projectId);
    setActiveView(nextView);
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
          <HomeWorkspace
            loadState={loadState}
            health={health}
            error={error}
            statusMessage={statusMessage}
            projects={projects}
            runsCount={runs.length}
            selectedProject={selectedProject}
            preferredProvider={preferredProvider}
            followUpProjects={followUpProjects}
            providers={providers}
            setActiveView={setActiveView}
          />
        ) : null}

        {activeView === "projects" ? (
          <ProjectsWorkspace
            projects={projects}
            selectedProjectId={selectedProjectId}
            setSelectedProjectId={setSelectedProjectId}
            statusMessage={statusMessage}
            prioritizedProjects={prioritizedProjects}
            projectNameDraft={projectNameDraft}
            setProjectNameDraft={setProjectNameDraft}
            projectPathDraft={projectPathDraft}
            setProjectPathDraft={setProjectPathDraft}
            projectAgentDraft={projectAgentDraft}
            setProjectAgentDraft={setProjectAgentDraft}
            createProject={createProject}
            projectSubmitting={projectSubmitting}
            selectedProject={selectedProject}
            focusProject={focusProject}
          />
        ) : null}

        {activeView === "providers" ? (
          <ProvidersWorkspace
            statusMessage={statusMessage}
            providers={providers}
            providerDrafts={providerDrafts}
            setProviderDrafts={setProviderDrafts}
            saveProviderConfig={saveProviderConfig}
            installProviderDependency={installProviderDependency}
            installingProviderId={installingProviderId}
            lastInstallResult={lastInstallResult}
          />
        ) : null}

        {activeView === "run" ? (
          <RunWorkspace
            statusMessage={statusMessage}
            runGuidance={runGuidance}
            setActiveView={setActiveView}
            runInFlight={runInFlight}
            runJob={runJob}
            jobPollCount={jobPollCount}
            activeRunSummary={activeRunSummary}
            workflowRefreshing={workflowRefreshing}
            refreshWorkflowRuns={refreshWorkflowRuns}
            selectedProjectId={selectedProjectId}
            trackedArtifacts={trackedArtifacts}
            trackedRunDetail={trackedRunDetail}
            setSelectedRunId={setSelectedRunId}
            setSelectedArtifactTitle={setSelectedArtifactTitle}
            runPrompt={runPrompt}
            setRunPrompt={setRunPrompt}
            runBlockerMessage={runBlockerMessage}
            submitRun={submitRun}
            runSubmitting={runSubmitting}
            runResult={runResult}
            selectedProject={selectedProject}
          />
        ) : null}

        {activeView === "workflow" ? (
          <WorkflowWorkspace
            statusMessage={statusMessage}
            workflowRefreshing={workflowRefreshing}
            selectedProjectId={selectedProjectId}
            refreshWorkflowRuns={refreshWorkflowRuns}
            runInFlight={runInFlight}
            runJob={runJob}
            jobPollCount={jobPollCount}
            runs={runs}
            selectedRunId={selectedRunId}
            setSelectedRunId={setSelectedRunId}
            runDetail={runDetail}
            selectedArtifactTitle={selectedArtifactTitle}
            setSelectedArtifactTitle={setSelectedArtifactTitle}
          />
        ) : null}
      </main>
    </div>
  );
}
