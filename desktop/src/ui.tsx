import type { WorkflowArtifactDocument } from "./types";

export function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="metric-card">
      <p>{label}</p>
      <strong>{value}</strong>
    </article>
  );
}

export function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="summary-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}

export function ArtifactViewer({ artifact }: { artifact: WorkflowArtifactDocument }) {
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
