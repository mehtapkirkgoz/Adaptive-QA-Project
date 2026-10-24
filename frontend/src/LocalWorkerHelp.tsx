type Props = {licensed: boolean; references: string[]};

export function LocalWorkerHelp({licensed, references}: Props) {
  const command = licensed
    ? 'python -m adaptive_qa local worker-cycle --workspace C:/QA/workspace --trusted-keys C:/QA/publisher-public-keys.json'
    : 'python -m adaptive_qa dashboard free-worker-cycle --database C:/QA/workspace/projects.sqlite';
  return <details className="local-worker-help">
    <summary>Run queued jobs locally</summary>
    <p>Open another terminal in your installed application environment. Use the same workspace as this dashboard. Replace the example paths below with your own paths.</p>
    {!!references.length && <>
      <p>Set these saved input references in that terminal before starting the worker. Keep their values on this computer; do not paste them into this dashboard or a support report.</p>
      <ul>{references.map(reference => <li key={reference}><code>{reference}</code></li>)}</ul>
    </>}
    <p>Run one bounded queue cycle:</p>
    <pre><code>{command}</code></pre>
    <p>The command attempts at most one discovery job, one read-only run and one confirmed form job, then exits. Queued jobs wait until a worker runs. It does not create jobs or retry uncertain submissions.</p>
    {licensed && <p>Use the publisher's public-key file, never a private signing key. A currently valid license and available capacity are required.</p>}
  </details>;
}
