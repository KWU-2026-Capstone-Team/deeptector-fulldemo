import { ACTIONS, CHECKLIST, HELP, LAW_NOTE } from "@/lib/education";

/** Shared "how to spot / what to do" section shown after a game or an analysis. */
export function LearnPanel({ intro }: { intro?: string }) {
  return (
    <section className="card learn-panel" aria-label="딥페이크 대응 가이드">
      <p className="kicker">DEEPFAKE LITERACY</p>
      <h2>딥페이크, 이렇게 확인하고 대응하세요</h2>
      {intro && <p className="muted">{intro}</p>}
      <div className="learn-checklist">
        {CHECKLIST.map((item, index) => (
          <article key={item.title}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <div><b>{item.title}</b><p>{item.body}</p></div>
          </article>
        ))}
      </div>
      <div className="learn-columns">
        <div>
          <h3>의심될 때 행동 요령</h3>
          <ol className="learn-actions">{ACTIONS.map((text) => <li key={text}>{text}</li>)}</ol>
        </div>
        <div>
          <h3>도움받을 곳</h3>
          <ul className="learn-help">
            {HELP.map((item) => <li key={item.name}><b>{item.name}</b><span className="contact">{item.contact}</span><small>{item.role}</small></li>)}
          </ul>
          <p className="learn-law">{LAW_NOTE}</p>
        </div>
      </div>
    </section>
  );
}
