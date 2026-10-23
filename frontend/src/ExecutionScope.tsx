type Settings = {configured: boolean; base_url?: string; allowed_hosts?: string[]};

export function supportsLocalDiscovery(settings: Settings) {
  const origin = 'http://127.0.0.1:8000', url = settings.base_url ?? '';
  if (!settings.configured || !url.startsWith(origin) || !(settings.allowed_hosts ?? []).includes('127.0.0.1')) return false;
  const path = url.slice(origin.length) || '/';
  return path.length <= 512 && path.startsWith('/') && !path.startsWith('//') && !/[\\%?#:]|[^\x21-\x7e]/.test(path)
    && !path.split('/').some(part => part === '.' || part === '..');
}

export function matchesSavedTarget(settings: Settings, binding: {target_binding?: string | null; document_path?: string | null}) {
  if (!supportsLocalDiscovery(settings)) return false;
  const path = settings.base_url?.slice('http://127.0.0.1:8000'.length) || '/';
  return path === '/' ? binding.target_binding === 'local_root'
    : binding.target_binding === 'local_document' && binding.document_path === path;
}

export function ExecutionScope({settings}: {settings: Settings}) {
  return <section className="execution-scope" aria-label="Saved target execution support">
    <h3>Execution support</h3>
    {!settings.configured ? <p>Save target settings to check available execution.</p> : supportsLocalDiscovery(settings)
      ? <p>This saved target supports controlled local discovery. Non-root paths support the five
        independent document checks; other UI checks still require a compatible root binding.</p>
      : <p>Execution is unavailable for this saved target. The current local worker supports only
        canonical document paths at http://127.0.0.1:8000/ with 127.0.0.1 in allowed hosts. Other targets can be saved and their
        configuration reviewed, but cannot be discovered or tested by this worker.</p>}
    <p className="hint">This describes saved settings. Unsaved edits are excluded. Supported targets still
      require a running fixture, current access, available capacity and explicit test selection.
      API and database checks require separately supported bindings.</p>
  </section>;
}
