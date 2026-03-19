const surfaces = [
  "Home",
  "Projects",
  "Run",
  "Workflow",
  "Providers",
];

export function App() {
  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">AOP Desktop</p>
        <h1>Workflow-first local app for idea to MVP execution.</h1>
        <p className="lede">
          This scaffold is the starting point for replacing the legacy Streamlit
          dashboard with a desktop shell built on top of the new app runtime
          bridge.
        </p>
      </section>

      <section className="grid">
        {surfaces.map((surface) => (
          <article key={surface} className="card">
            <h2>{surface}</h2>
            <p>
              Planned desktop MVP surface for the next AOP iteration.
            </p>
          </article>
        ))}
      </section>
    </main>
  );
}
