import {useEffect, useRef, useState} from 'react';

type Result = {case_id: string; status: string; message: string; duration_seconds: number; evidence_id?: string};
type Check = {check_id: string; project_id: string; url: string; status: string; inspected_pages?: number;
  requested?: number; not_run?: number; names?: Record<string, string>; results?: Result[]; run_id?: string};
type Props = {request: <T>(path: string, method?: string, body?: unknown) => Promise<T>; onAdvanced: () => void};
const names: Record<string, string> = {'DOC-001': 'Sayfanın başlığı var mı?', 'DOC-002': 'Sayfanın dili tanımlanmış mı?',
  'DOC-003': 'Sayfa öğelerinin kimlikleri benzersiz mi?', 'DOC-004': 'Erişilebilirlik etiketleri doğru öğelere bağlı mı?',
  'DOC-005': 'Sayfa içi bağlantılar doğru yere gidiyor mu?', 'LOGIN-001': 'Giriş formunun alanları kullanılabilir mi?',
  'SEARCH-001': 'Arama formunun alanları kullanılabilir mi?'};
const active = (check: Check | null) => !!check && ['discovering', 'testing', 'cancelling'].includes(check.status);
const stages: Record<string, string> = {discovering: 'Site inceleniyor…', testing: 'Uygun testler çalıştırılıyor…',
  cancelling: 'İşlem durduruluyor…', completed: 'Kontrol tamamlandı', cancelled: 'Kontrol durduruldu',
  error: 'Kontrol tamamlanamadı', interrupted: 'Uygulama kapandığı için kontrol yarıda kaldı', no_tests: 'Bu adres için çalıştırılabilir test bulunamadı'};

export function SiteCheck({request, onAdvanced}: Props) {
  const [url, setUrl] = useState(''), [check, setCheck] = useState<Check | null>(null);
  const [history, setHistory] = useState<Check[]>([]), [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const serial = useRef(0);
  useEffect(() => {let alive = true;
    request<{checks: Check[]}>('/api/site-checks').then(data => {
      if (!alive) return;
      setHistory(data.checks); setCheck(data.checks[0] ?? null); setUrl(data.checks[0]?.url ?? '');
    }).catch(() => {if (alive) setError('Önceki sonuçlar yüklenemedi. Sayfayı yenileyerek tekrar deneyebilirsin.');})
      .finally(() => {if (alive) setLoading(false);});
    return () => {alive = false;};
  }, []);
  useEffect(() => {
    if (!active(check)) return;
    let alive = true, timer: ReturnType<typeof setTimeout> | undefined;
    const id = check!.check_id, version = serial.current;
    async function poll() {
      try {
        const next = await request<Check>(`/api/site-checks/${id}`);
        if (!alive || version !== serial.current) return;
        setCheck(next);
        setHistory(previous => [next, ...previous.filter(item => item.check_id !== id)].slice(0, 20));
        if (active(next)) timer = setTimeout(poll, 1000);
      } catch {if (alive) setError('İlerleme bilgisi alınamadı. Sayfayı yenile; yeni test otomatik başlatılmaz.');}
    }
    timer = setTimeout(poll, 600);
    return () => {alive = false; clearTimeout(timer);};
  }, [check?.check_id, check?.status]);
  async function start() {
    setBusy(true); setError(''); serial.current += 1;
    try {
      const next = await request<Check>('/api/site-checks', 'POST', {url: url.trim()});
      setCheck(next); setHistory(previous => [next, ...previous].slice(0, 20));
    } catch {setError('Test başlatılamadı. https:// ile başlayan geçerli bir adres kullan. Başka bir kontrol sürüyor veya projenin gelişmiş ayarları korunuyor olabilir.');}
    finally {setBusy(false);}
  }
  const results = check?.results ?? [];
  const passed = results.filter(result => result.status === 'passed');
  const failed = results.filter(result => result.status === 'failed');
  const other = results.filter(result => !['passed', 'failed'].includes(result.status));
  const unrecorded = Math.max(0, (check?.requested ?? 0) - results.length);
  const groups = [{title: 'Geçen testler', items: passed, kind: 'passed'},
    {title: 'Başarısız testler', items: failed, kind: 'failed'}, {title: 'Tamamlanamayan testler', items: other, kind: 'other'}];
  return <div className="site-check-shell"><header className="site-check-header"><a className="brand" href="/"> <span className="mark">AQ</span> Adaptive QA</a>
    <button className="quiet" onClick={onAdvanced}>Gelişmiş ayarlar</button></header>
    <main className="site-check-main"><section className="site-check-hero"><p className="eyebrow">SEN ADRESİ YAZ, KONTROLLERİ BİZ ÇALIŞTIRALIM</p>
      <h1>Siteni test et.</h1><p>Site adresini gir. Uygun kontrolleri otomatik seçelim; geçenleri ve sorunları tek ekranda gösterelim.</p>
      <form onSubmit={event => {event.preventDefault(); void start();}} className="site-check-form">
        <label htmlFor="site-url">Test edilecek site adresi</label><div className="site-check-input">
          <input id="site-url" type="url" required maxLength={512} placeholder="https://ornek.com" value={url}
            disabled={busy || active(check)} onChange={event => setUrl(event.target.value)}/>
          <button className="primary" type="submit" disabled={loading || busy || active(check)}>{busy ? 'Başlatılıyor…' : active(check) ? 'Test sürüyor…' : 'Test et'}</button></div>
        <p className="hint">İlk kontrol yalnızca sayfaları okur. Giriş yapmaz, form göndermez, verileri değiştirmez. Sonuçlar bu bilgisayarda kalır.</p>
      </form>
      <ol className="site-check-steps"><li>1 · Adresi gir</li><li>2 · Otomatik kontrol</li><li>3 · Sonuçları gör</li></ol>
    </section>
    {error && <p role="alert" className="message error">{error}</p>}
    {loading && <p role="status">Yerel çalışma alanı açılıyor…</p>}
    {check && <section className="card site-check-results" aria-label="Site kontrol sonuçları">
      <div className="section-label"><div><h2 aria-live="polite">{stages[check.status] ?? 'Kontrol bekleniyor'}</h2><p className="site-check-url">{check.url}</p></div>
        {active(check) && <button disabled={busy || check.status === 'cancelling'} onClick={async () => {
          setBusy(true); try {setCheck(await request<Check>(`/api/site-checks/${check.check_id}/cancel`, 'POST', {}));}
          catch {setError('Durdurma isteği iletilemedi. Durumu yenileyip tekrar dene.');} finally {setBusy(false);}
        }}>Durdur</button>}</div>
      {active(check) && <p role="status" className="site-check-progress">{check.status === 'discovering'
        ? 'Sayfalar ve kullanılabilir özellikler inceleniyor. Hiçbir ayar veya komut girmen gerekmiyor.'
        : check.status === 'testing' ? `${results.length} / ${check.requested ?? 0} test sonucu hazır. Kontroller arka planda sürüyor.` : 'Güvenli şekilde durduruluyor…'}</p>}
      <div className="site-check-totals"><div><strong>{passed.length}</strong><span>Geçti</span></div><div><strong>{failed.length}</strong><span>Başarısız</span></div>
        <div><strong>{other.length}</strong><span>Tamamlanamadı</span></div><div><strong>{check.inspected_pages ?? '—'}</strong><span>İncelenen sayfa</span></div></div>
      {!active(check) && ['error', 'interrupted'].includes(check.status) && <p className="message error">Siteye erişim, güvenlik sınırı veya çalışma ortamı nedeniyle işlem tamamlanamadı. Bu sonuç sitenin hatalı olduğunu göstermez. Kaydedilmiş sonuçlar aşağıda; yeniden denemek için Test et düğmesini kullan.</p>}
      {groups.map(group => !!group.items.length && <section className={`site-check-group ${group.kind}`} key={group.kind}><h3>{group.title} · {group.items.length}</h3>
        {group.items.map(result => <article key={result.case_id}><strong>{names[result.case_id] ?? check.names?.[result.case_id] ?? result.case_id}</strong>
          <p>{result.status === 'passed' ? 'Bu kontrolün beklenen koşulları sağlandı.' : result.status === 'failed'
            ? 'Beklenen koşul sağlanmadı. Test ayrıntısını inceleyebilirsin.' : 'Kontrol güvenilir bir sonuç üretemedi; başarısız test olarak sayılmadı.'}</p>
          <details><summary>Test ayrıntısı</summary><p>{check.names?.[result.case_id]} · {result.case_id} · {result.duration_seconds.toFixed(2)} sn · {result.status}</p><p>{result.message}</p></details>
          {result.evidence_id && check.run_id && <a target="_blank" rel="noopener noreferrer" href={`/api/projects/${check.project_id}/runs/${check.run_id}/evidence/${result.evidence_id}`}>Ekran görüntüsü</a>}
        </article>)}</section>)}
      {!active(check) && <p className="hint">Bu kontrol tüm site için başarı garantisi değildir. En fazla 5 sayfa keşfedilir ve uygun bulunan en fazla 10 salt okunur test çalıştırılır.
        {check.not_run !== undefined && ` Katalogdaki ${check.not_run} kontrol bu koşuya alınmadı.`}
        {unrecorded > 0 && ` Seçilen ${unrecorded} test için sonuç üretilemedi.`} Giriş, API ve veritabanı kontrolleri ek yapılandırma gerektirir.</p>}
    </section>}
    {history.length > 1 && <section className="site-check-history"><h2>Önceki kontroller</h2>{history.slice(1).map(item => <button key={item.check_id} disabled={active(check) || busy}
      onClick={() => {serial.current += 1; setCheck(item); setUrl(item.url); setHistory(previous => [item, ...previous.filter(row => row.check_id !== item.check_id)]);}}>{item.url}<span>{stages[item.status] ?? item.status}</span></button>)}</section>}
    </main><footer>ADAPTIVE QA <span>Yerel çalışma · Açık sonuçlar</span></footer></div>;
}
