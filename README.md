# Adaptive-QA-Project

URL üzerinden web uygulamalarını keşfeden, mevcut özelliklerine uygun UI, API ve veritabanı testlerini çalıştıran yapay zekâ destekli bir QA platformu.

**Durum:** Sprint 0 başladı (18 Ekim 2026). Aşama 0.1: proje iskeleti hazır; test motoru henüz uygulanmadı.

## Ürün deneyimi

Kullanıcı web arayüzünde bir proje oluşturur, hedef URL ve gerekli test ayarlarını girer, test planını inceleyip çalıştırır. Testler arka plandaki worker süreçlerinde yürütülür. Sonuçlar, ekran görüntüleri ve geçmiş koşular panelden görüntülenir.

Domain web paneline erişim sağlar; uzun süren tarayıcı testleri web isteğinden bağımsız çalışır. Müşterinin özel ağı içindeki sistemler için ileride müşteri ortamında çalışan bir agent seçeneği sağlanır.

## Planlanan bileşenler

- Web paneli ve uygulama API'si.
- İş kuyruğu ve izole test worker'ları.
- UI, API ve veritabanı test katmanları.
- Yapılandırılmış keşif, test seçimi ve element bulma için değiştirilebilir yapay zekâ katmanı.
- Proje yapılandırması, güvenli sır yönetimi, rapor ve kanıt depolama.

Teknoloji kararları [mimari kaydında](docs/ARCHITECTURE.md) tutulur.

## Sprint takibi

Sprintler yaklaşık iki haftalık çalışma hedefleridir; tarihler kapasite ve kapsam netleşince belirlenir. Bir sprint yalnızca kabul koşulları doğrulandığında tamamlanır.

| Sprint | Hedef | Durum | Tamamlanan işler |
|---|---|---|---|
| 0 | Temel mimari ve GitHub düzeni | Devam ediyor | Python iskeleti, mimari, CI tanımı, issue/PR şablonları |
| 1 | Çalışan ilk test akışı | Planlandı | — |
| 2 | Keşif ve özellik tespiti | Planlandı | — |
| 3 | UI test havuzu ve element eşleştirme | Planlandı | — |
| 4 | API testleri | Planlandı | — |
| 5 | Veritabanı doğrulamaları | Planlandı | — |
| 6 | Yapay zekâ entegrasyonu | Planlandı | — |
| 7 | Web paneli ve proje yönetimi | Planlandı | — |
| 8 | Raporlama ve test havuzunun büyütülmesi | Planlandı | — |
| 9 | Domain, staging ve üretim dağıtımı | Planlandı | — |
| 10 | Müşterili kullanım ve pilot | Planlandı | — |

Her sprint sonunda bu tabloya gerçekten teslim edilen işler ve ilgili PR/sürüm bağlantısı eklenir. Ayrıntılar [sprint planında](docs/SPRINT_PLAN.md), çalışma kuralları [GitHub iş akışında](docs/GITHUB_WORKFLOW.md) tutulur.

## Temel kalite ilkeleri

- Özelliğin bulunamaması ile mevcut olmadığının doğrulanması farklı sonuçlardır.
- Sonuçlar başarılı, başarısız, atlandı, engellendi ve çalıştırma hatası olarak ayrılır.
- Test başarı ölçütleri açıkça tanımlanır; yapay zekâ sonucu geçirmek için bunları değiştiremez.
- Yalnızca proje için izin verilmiş hedeflerde test çalıştırılır; veri değiştiren işlemler proje politikasıyla kontrol edilir.
- Hesap bilgileri, token'lar ve bağlantı sırları kaynak koda veya raporlara yazılmaz.

## Geliştirme

Kurulum komutları: [Geliştirici kurulumu](docs/SETUP.md). Ayrıntılı ilerleme: [Sprint 0](docs/SPRINT_0.md).

Bu aşamada mimari kaydı, kurulabilir Python paketi, durum komutu, temel CI tanımı, GitHub issue/PR şablonları ve geliştirme ayarları eklendi. CI henüz GitHub üzerinde çalıştırılmadı. Commit ve push kullanıcı tarafından yapılır.
