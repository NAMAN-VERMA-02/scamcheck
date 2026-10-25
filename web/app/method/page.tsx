export const metadata = { title: "Method · ScamCheck" };

export default function Method() {
  return (
    <article className="prose">
      <h1 className="h1">Method</h1>
      <p className="lede">
        The research question: can a transparent, evidence-first checker for English and Hinglish messages be measured
        honestly — false alarms per legitimate category, dangerous misses, abstention, the language gap and robustness
        to obfuscation — and how does it compare with simple baselines?
      </p>

      <h2 className="h2">One engine, two uses</h2>
      <p>
        The page you use to analyse a message and the offline benchmark call the same Python function. There is no
        separate demo scoring path. Stages: Unicode normalisation (hidden characters and lookalike letters are removed
        and recorded as signals) → versioned rule pack → static link structure → optional language model on redacted
        text → a pure verdict combiner → explanations generated only from signals that fired.
      </p>

      <h2 className="h2">Verdict policy</h2>
      <ul>
        <li>
          Any <strong>HIGH</strong> rule or link signal gives <code>LIKELY_SCAM</code>. A language model cannot overrule it.
        </li>
        <li>
          A model can raise a verdict to <code>LIKELY_SCAM</code> only by quoting text that actually appears in the
          message.
        </li>
        <li>
          <code>NO_STRONG_SIGNALS</code> needs a working model that found nothing <em>and</em> no medium or high signal,
          no obfuscation or injection, and no link whose destination was left unchecked.
        </li>
        <li>
          Without a model (the default) the engine abstains with <code>UNCLEAR</code> unless a HIGH signal fires. A model
          timeout or malformed answer is treated exactly like having no model.
        </li>
        <li>No probability or confidence percentage is shown: none of the scores here is calibrated.</li>
      </ul>

      <h2 className="h2">Privacy and link safety</h2>
      <ul>
        <li>Messages are analysed in memory. Nothing is stored; logs contain only method, path, status and latency.</li>
        <li>Links are parsed as text. They are never fetched, resolved or followed.</li>
        <li>
          Domain age, reputation and certificate history are <em>not</em> checked, and the interface says so rather than
          guessing.
        </li>
        <li>
          The model is off unless the operator configures one and you tick the opt-in for that request. Identifiers are
          replaced with placeholders first; this is redaction assistance, not anonymisation.
        </li>
      </ul>

      <h2 className="h2">What the numbers mean</h2>
      <p>
        The bundled benchmark and robustness data are synthetic, written by the same person who wrote the rules. They
        show that the measurement pipeline works and expose concrete failure modes; they are not evidence of
        real-world accuracy. Real claims require consented, redacted, double-annotated messages and a frozen test split,
        as described in the repository documentation.
      </p>
    </article>
  );
}
