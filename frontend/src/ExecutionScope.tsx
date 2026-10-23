type Settings = {configured: boolean; base_url?: string; allowed_hosts?: string[];
  discovery_support?: {supported: boolean; profile: string | null; execution_scope: string}};

export function supportsDiscovery(settings: Settings) {
  return settings.discovery_support?.supported ?? supportsLocalDiscovery(settings);
}

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
    {!settings.configured ? <p>Save target settings to check available execution.</p>
      : settings.discovery_support?.profile === 'public_https'
      ? <p>Read-only HTTPS discovery is available for this saved host scope. It does not sign in or submit forms.
        External UI, API and database execution are not enabled by this profile.</p> : supportsLocalDiscovery(settings)
      ? <p>This saved target supports controlled local discovery. Non-root paths support the five
        independent document checks; other UI checks still require a compatible root binding.</p>
      : <p>Execution is unavailable for this saved target. Supported discovery profiles are public HTTPS on port 443
        with explicit allowed hosts, or canonical controlled documents at http://127.0.0.1:8000/.
        Other targets can be saved and reviewed but cannot be discovered by this worker.</p>}
    <p className="hint">This describes saved settings. Unsaved edits are excluded. Supported targets still
      require current access and available capacity. Test execution requires separate supported bindings and explicit selection.
      API and database checks require separately supported bindings.</p>
  </section>;
}
