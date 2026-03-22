import { useMemo, useState } from "react";

import type {
  DesktopSetupCheck,
  DesktopProjectSummary,
  DesktopRunJob,
  DesktopRunLaunchResult,
  WorkflowArtifactDocument,
  WorkflowRunDetail,
  WorkflowRunSummary,
} from "./types";
import { ArtifactViewer, EmptyState, SummaryItem } from "./ui";

function formatTags(tags: string[]) {
  if (tags.length === 0) {
    return "unlabeled";
  }
  return tags.join(" / ").split("_").join(" ");
}

type RunWorkspaceProps = {
  statusMessage: string;
  runGuidance: { title: string; body: string };
  runBlockerAction: { label: string; view: "setup" | "projects" | "providers" | "workflow" };
  setActiveView: (view: "setup" | "projects" | "providers" | "workflow") => void;
  runInFlight: boolean;
  runJob: DesktopRunJob | null;
  jobPollCount: number;
  activeRunSummary: WorkflowRunSummary | null;
  workflowRefreshing: boolean;
  refreshWorkflowRuns: (nextRunId?: string, projectIdOverride?: string) => Promise<void>;
  selectedProjectId: string;
  trackedArtifacts: WorkflowArtifactDocument[];
  trackedRunDetail: WorkflowRunDetail | null;
  setSelectedRunId: (runId: string) => void;
  setSelectedArtifactTitle: (title: string) => void;
  runPrompt: string;
  setRunPrompt: (value: string) => void;
  runBlockerMessage: string;
  requiredSetupBlockers: DesktopSetupCheck[];
  submitRun: () => Promise<void>;
  runSubmitting: boolean;
  runResult: DesktopRunLaunchResult | null;
  selectedProject: DesktopProjectSummary | null;
};

export function RunWorkspace(props: RunWorkspaceProps) {
  const {
    statusMessage,
    runGuidance,
    runBlockerAction,
    setActiveView,
    runInFlight,
    runJob,
    jobPollCount,
    activeRunSummary,
    workflowRefreshing,
    refreshWorkflowRuns,
    selectedProjectId,
    trackedArtifacts,
    trackedRunDetail,
    setSelectedRunId,
    setSelectedArtifactTitle,
    runPrompt,
    setRunPrompt,
    runBlockerMessage,
    requiredSetupBlockers,
    submitRun,
    runSubmitting,
    runResult,
    selectedProject,
  } = props;

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <p className="panel-eyebrow">Run</p>
          <h2>Start a workflow from desktop</h2>
        </div>
      </div>
      <div className="run-composer">
        {statusMessage ? <section className="status-banner">{statusMessage}</section> : null}
        <div className="run-guidance-card">
          <div>
            <p className="panel-eyebrow">Recommended next action</p>
            <h3>{runGuidance.title}</h3>
            <p>{runGuidance.body}</p>
          </div>
          <div className="provider-actions">
            <button type="button" className="action-button" onClick={() => setActiveView("workflow")}>
              Open workflow
            </button>
            <button type="button" className="action-button" onClick={() => setActiveView("providers")}>
              Check providers
            </button>
          </div>
        </div>
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
              <button type="button" className="action-button" onClick={() => setActiveView("workflow")}>
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
        {(runInFlight || runResult) && (activeRunSummary || trackedRunDetail) ? (
          <div className="run-progress-grid">
            <SummaryItem label="Run id" value={activeRunSummary?.run_id || runResult?.sprint_id || "-"} />
            <SummaryItem label="Phase" value={activeRunSummary?.current_phase || "waiting"} />
            <SummaryItem label="Verify" value={activeRunSummary?.verification_verdict || "-"} />
            <SummaryItem label="Completion" value={activeRunSummary?.completion_status || runResult?.state || "-"} />
          </div>
        ) : null}
        {trackedArtifacts.length > 0 ? (
          <div className="artifact-snapshot-card">
            <div className="panel-head">
              <div>
                <p className="panel-eyebrow">Live artifact snapshot</p>
                <h3>{trackedRunDetail?.summary.run_id}</h3>
              </div>
              <span className="pill pill-good">{trackedArtifacts.length} ready</span>
            </div>
            <div className="artifact-snapshot-list">
              {trackedArtifacts.slice(0, 4).map((artifact) => (
                <button
                  key={artifact.title}
                  type="button"
                  className="artifact-snapshot-button"
                  onClick={() => {
                    setSelectedRunId(trackedRunDetail?.summary.run_id || "");
                    setSelectedArtifactTitle(artifact.title);
                    setActiveView("workflow");
                  }}
                >
                  <strong>{artifact.title}</strong>
                  <span>{artifact.filename}</span>
                </button>
              ))}
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
        {runBlockerMessage && requiredSetupBlockers.length > 0 ? (
          <div className="run-guidance-card">
            <div>
              <p className="panel-eyebrow">Run is blocked by setup</p>
              <h3>{requiredSetupBlockers[0].label} needs attention</h3>
              <p>
                Fix the required setup blockers first, then come back here to launch the next workflow.
              </p>
            </div>
            <div className="provider-command-list">
              {requiredSetupBlockers.slice(0, 2).map((check) => (
                <code key={check.check_id}>{check.install_hint}</code>
              ))}
            </div>
          </div>
        ) : null}
        <div className="provider-actions">
          <button
            type="button"
            className="action-button action-button-accent"
            onClick={() => void submitRun()}
            disabled={runSubmitting || Boolean(runBlockerMessage)}
          >
            {runSubmitting ? "Running..." : "Start run"}
          </button>
          {runBlockerMessage ? (
            <button
              type="button"
              className="action-button"
              onClick={() => setActiveView(runBlockerAction.view)}
            >
              {runBlockerAction.label}
            </button>
          ) : null}
          {runJob?.sprint_id ? (
            <button type="button" className="action-button" onClick={() => setActiveView("workflow")}>
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
  );
}

type WorkflowWorkspaceProps = {
  statusMessage: string;
  workflowRefreshing: boolean;
  selectedProjectId: string;
  refreshWorkflowRuns: (nextRunId?: string, projectIdOverride?: string) => Promise<void>;
  runInFlight: boolean;
  runJob: DesktopRunJob | null;
  jobPollCount: number;
  runs: WorkflowRunSummary[];
  selectedRunId: string;
  setSelectedRunId: (runId: string) => void;
  runDetail: WorkflowRunDetail | null;
  selectedArtifactTitle: string;
  setSelectedArtifactTitle: (title: string) => void;
};

export function WorkflowWorkspace(props: WorkflowWorkspaceProps) {
  const {
    statusMessage,
    workflowRefreshing,
    selectedProjectId,
    refreshWorkflowRuns,
    runInFlight,
    runJob,
    jobPollCount,
    runs,
    selectedRunId,
    setSelectedRunId,
    runDetail,
    selectedArtifactTitle,
    setSelectedArtifactTitle,
  } = props;
  const [runFilter, setRunFilter] = useState<"all" | "follow_up" | "flaky" | "stable">("all");

  const selectedArtifact =
    runDetail?.artifacts.find((artifact) => artifact.title === selectedArtifactTitle) ?? null;
  const sortedRuns = useMemo(() => {
    return [...runs].sort((left, right) => {
      if (left.priority_rank !== right.priority_rank) {
        return right.priority_rank - left.priority_rank;
      }
      return (right.updated_at || "").localeCompare(left.updated_at || "");
    });
  }, [runs]);
  const visibleRuns = useMemo(() => {
    if (runFilter === "follow_up") {
      return sortedRuns.filter((run) => run.attention_tags.includes("needs_follow_up"));
    }
    if (runFilter === "stable") {
      return sortedRuns.filter((run) => run.attention_tags.includes("stable"));
    }
    if (runFilter === "flaky") {
      return sortedRuns.filter((run) => run.attention_tags.includes("flaky"));
    }
    return sortedRuns;
  }, [runFilter, sortedRuns]);
  const followUpCount = useMemo(
    () => sortedRuns.filter((run) => run.attention_tags.includes("needs_follow_up")).length,
    [sortedRuns],
  );
  const flakyCount = useMemo(
    () => sortedRuns.filter((run) => run.attention_tags.includes("flaky")).length,
    [sortedRuns],
  );
  const previousRun = useMemo(() => {
    if (!runDetail) {
      return null;
    }
    const currentIndex = sortedRuns.findIndex((run) => run.run_id === runDetail.summary.run_id);
    if (currentIndex < 0) {
      return null;
    }
    return sortedRuns[currentIndex + 1] ?? null;
  }, [runDetail, sortedRuns]);
  const workflowGuidance = useMemo(() => {
    if (runDetail?.summary.has_guardrails) {
      return {
        title: "Open guardrails or completion artifacts first",
        body: "The selected run hit a stop condition. Review guardrails and completion before deciding whether to retry or repair.",
      };
    }
    if (runDetail?.summary.has_gaps) {
      return {
        title: "Verification needs follow-up",
        body: "The selected run still has gaps. Start with verification and gaps artifacts to understand what remains unresolved.",
      };
    }
    if (runDetail?.summary.status && runDetail.summary.status !== "completed") {
      return {
        title: "This run is still in motion",
        body: "Track execution and verification artifacts first. More complete artifacts should continue to land as the workflow progresses.",
      };
    }
    return {
      title: "Review summary, then drill into artifacts",
      body: "This run looks stable. Use summary and completion to confirm the outcome, then inspect detailed artifacts only if something looks off.",
    };
  }, [runDetail?.summary.has_gaps, runDetail?.summary.has_guardrails, runDetail?.summary.status]);
  const recommendedArtifactTitle = useMemo(() => {
    if (!runDetail) {
      return "";
    }
    const priorities = runDetail.summary.has_guardrails
      ? ["GUARDRAILS", "COMPLETION", "VERIFICATION"]
      : runDetail.summary.has_gaps
        ? ["VERIFICATION", "GAPS", "COMPLETION"]
        : runDetail.summary.status !== "completed"
          ? ["EXECUTION", "RUN", "SUMMARY"]
          : ["SUMMARY", "COMPLETION", "LEARNINGS"];
    for (const keyword of priorities) {
      const match = runDetail.artifacts.find((artifact) => artifact.title.toUpperCase().includes(keyword));
      if (match) {
        return match.title;
      }
    }
    return runDetail.artifacts.find((artifact) => artifact.exists)?.title || runDetail.artifacts[0]?.title || "";
  }, [runDetail]);

  return (
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
      <div className="workflow-guidance-card">
        <div>
          <p className="panel-eyebrow">Recommended workflow review</p>
          <h3>{workflowGuidance.title}</h3>
          <p>{workflowGuidance.body}</p>
        </div>
        <div className="summary-row">
          <SummaryItem label="Runs" value={String(runs.length)} />
          <SummaryItem label="Follow-up" value={String(followUpCount)} />
          <SummaryItem label="Flaky" value={String(flakyCount)} />
          <SummaryItem label="Filter" value={runFilter.replace("_", " ")} />
          <SummaryItem label="Focus artifact" value={recommendedArtifactTitle || "-"} />
        </div>
        <div className="provider-actions">
          <button
            type="button"
            className={`action-button ${runFilter === "all" ? "action-button-accent" : ""}`}
            onClick={() => setRunFilter("all")}
          >
            All runs
          </button>
          <button
            type="button"
            className={`action-button ${runFilter === "follow_up" ? "action-button-accent" : ""}`}
            onClick={() => setRunFilter("follow_up")}
          >
            Follow-up
          </button>
          <button
            type="button"
            className={`action-button ${runFilter === "flaky" ? "action-button-accent" : ""}`}
            onClick={() => setRunFilter("flaky")}
          >
            Flaky
          </button>
          <button
            type="button"
            className={`action-button ${runFilter === "stable" ? "action-button-accent" : ""}`}
            onClick={() => setRunFilter("stable")}
          >
            Stable
          </button>
          {recommendedArtifactTitle ? (
            <button
              type="button"
              className="action-button"
              onClick={() => setSelectedArtifactTitle(recommendedArtifactTitle)}
            >
              Open suggested artifact
            </button>
          ) : null}
        </div>
      </div>
      {runDetail && previousRun ? (
        <div className="workflow-guidance-card">
          <div>
            <p className="panel-eyebrow">Compare with previous run</p>
            <h3>{runDetail.summary.run_id} vs {previousRun.run_id}</h3>
            <p>
              Compare whether this run improved the outcome, stalled in the same phase, or introduced new follow-up pressure.
            </p>
          </div>
          <div className="summary-row">
            <SummaryItem label="Status" value={`${previousRun.status} -> ${runDetail.summary.status}`} />
            <SummaryItem label="Phase" value={`${previousRun.current_phase || "-"} -> ${runDetail.summary.current_phase || "-"}`} />
            <SummaryItem label="Verify" value={`${previousRun.verification_verdict || "-"} -> ${runDetail.summary.verification_verdict || "-"}`} />
            <SummaryItem label="Completion" value={`${previousRun.completion_status || "-"} -> ${runDetail.summary.completion_status || "-"}`} />
          </div>
          <div className="summary-row">
            <SummaryItem
              label="Flags"
              value={`${formatTags(previousRun.attention_tags)} -> ${formatTags(runDetail.summary.attention_tags)}`}
            />
            <SummaryItem label="Previous run" value={previousRun.run_id} />
            <SummaryItem label="Current run" value={runDetail.summary.run_id} />
            <SummaryItem label="Updated" value={runDetail.summary.updated_at.replace("T", " ").slice(0, 19)} />
          </div>
          {runDetail.summary.triage_summary ? <p>{runDetail.summary.triage_summary}</p> : null}
          {runDetail.summary.triage_evidence.length > 0 ? (
            <div className="provider-command-list">
              {runDetail.summary.triage_evidence.slice(0, 3).map((item) => (
                <code key={item}>{item}</code>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
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
      {visibleRuns.length === 0 ? (
        <EmptyState
          title={runFilter === "all" ? "No workflow runs yet" : "No runs match this filter"}
          body={
            runFilter === "all"
              ? "Once a project starts producing workflow artifacts, runs will show up here."
              : "Try another filter or refresh runs after the next workflow update."
          }
        />
      ) : (
        <div className="workflow-layout">
          <div className="run-list">
            {visibleRuns.map((run) => (
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
                  <span className={`pill ${run.attention_tags.includes("needs_follow_up") ? "pill-warn" : "pill-good"}`}>
                    {run.attention_tags[0] || run.status}
                  </span>
                </div>
                <div className="summary-row">
                  <SummaryItem label="Phase" value={run.current_phase || "-"} />
                  <SummaryItem label="Verify" value={run.verification_verdict || "-"} />
                  <SummaryItem label="Completion" value={run.completion_status || "-"} />
                  <SummaryItem label="Labels" value={formatTags(run.attention_tags)} />
                </div>
                {run.triage_summary ? <p>{run.triage_summary}</p> : null}
                {run.triage_evidence.length > 0 ? (
                  <div className="provider-command-list">
                    {run.triage_evidence.slice(0, 2).map((item) => (
                      <code key={item}>{item}</code>
                    ))}
                  </div>
                ) : null}
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
                  <SummaryItem label="Labels" value={formatTags(runDetail.summary.attention_tags)} />
                  <SummaryItem
                    label="Artifacts"
                    value={String(runDetail.artifacts.filter((artifact) => artifact.exists).length)}
                  />
                </div>
                {runDetail.summary.triage_summary ? <p>{runDetail.summary.triage_summary}</p> : null}
                {runDetail.summary.triage_evidence.length > 0 ? (
                  <div className="provider-command-list">
                    {runDetail.summary.triage_evidence.map((item) => (
                      <code key={item}>{item}</code>
                    ))}
                  </div>
                ) : null}

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
              <EmptyState
                title="No run detail loaded"
                body="Choose a workflow run to inspect persisted artifacts."
              />
            )}
          </div>
        </div>
      )}
    </section>
  );
}
