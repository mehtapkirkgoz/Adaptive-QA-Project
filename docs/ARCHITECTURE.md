# Mimari kararı — ADR 001

Tarih: 18 Ekim 2026
Durum: İlk geliştirme için kabul edildi; bağımlılık sürümleri ilgili aşamada kilitlenecek.

## Teknoloji ve sınırlar

- Çekirdek: Python 3.13 ve üzeri; CI tabanı 3.13.
- UI otomasyonu: Playwright. Tarayıcı kurulumu Sprint 1'de eklenecek.
- Web API: FastAPI; panel HTTP API üzerinden iş başlatacak.
- Panel: React ve TypeScript; Sprint 7'de kurulacak.
- Kalıcı veri: PostgreSQL; projeler, koşular ve sonuçlar.
- İş kuyruğu: Redis ve Celery; API sürecinden ayrı worker.
- Kanıtlar: geliştirmede yerel dosyalar, dağıtımda erişim kontrollü nesne depolama.
- AI: sağlayıcı adaptörü arkasında; çekirdek model hizmeti olmadan da çalışacak.

Bugün yalnızca bağımlılıksız Python paket iskeleti vardır. Listelenen servisler henüz kurulmuş veya entegre edilmiş değildir.

## Akış

Panel → API → hedef/politika doğrulama → kuyruk → worker → keşif/test planı → test adaptörleri → sonuç ve kanıt depolama → panel.

Web süreci tarayıcı testi çalıştırmaz. İşler timeout, iptal ve kaynak temizleme sınırlarına sahip olur. Her sorgu ve kanıt erişimi proje/organizasyon yetkisiyle sınırlandırılır. Keşfedilen URL'ler ve yönlendirmeler de hedef politikasından geçer.

## Gerekçe

Python çekirdeği UI, API, SQL ve AI adaptörlerini ortak dilde tutar. Ayrı worker uzun koşuların web panelini bloke etmesini önler. Başlangıçta tek depo ve modüler uygulama kullanılır; ayrı mikroservis depolarına ihtiyaç doğmadan bölünmez.

## Sonraki kararlar

Test case sözleşmesi, sonuç modeli, sır yönetimi, müşteri agent protokolü ve AI sağlayıcısı ayrı kararlarla netleştirilecek.

## Kaynaklar

- https://playwright.dev/python/docs/library
- https://playwright.dev/python/docs/browsers
