type Settings = {configured: boolean; base_url?: string; allowed_hosts?: string[]};

export function supportsLocalDiscovery(settings: Settings) {
  return settings.configured && ['http://127.0.0.1:8000', 'http://127.0.0.1:8000/'].includes(settings.base_url ?? '')
    && (settings.allowed_hosts ?? []).includes('127.0.0.1');
}

export function ExecutionScope({settings}: {settings: Settings}) {
  return <section className="execution-scope" aria-label="Saved target execution support">
    <h3>Execution support</h3>
    {!settings.configured ? <p>Save target settings to check available execution.</p> : supportsLocalDiscovery(settings)
      ? <p>This saved target supports controlled local discovery and eligible UI tests.</p>
      : <p>Execution is unavailable for this saved target. The current local worker supports only
        http://127.0.0.1:8000/ with 127.0.0.1 in allowed hosts. Other targets can be saved and their
        configuration reviewed, but cannot be discovered or tested by this worker.</p>}
    <p className="hint">This describes saved settings. Unsaved edits are excluded. Supported targets still
      require a running fixture, current access, available capacity and explicit test selection.
      API and database checks require separately supported bindings.</p>
  </section>;
}
