# Sprint planı

## Planlama çerçevesi

Sprint 0 için yaklaşık bir hafta, diğer sprintler için yaklaşık iki hafta hedeflenir. Bunlar teslim tarihi taahhüdü değildir. Takvim, ekip kapasitesi ve Sprint 0 kararlarıyla kesinleşir. İlk teknik gösterim Sprint 1'de, bütünleşik MVP Sprint 7 sonunda, pilot aday Sprint 9 sonunda hedeflenir.

Test case sayısı varyasyonlarla şişirilmez: her case'in kimliği, ön koşulları, adımları, beklenen sonucu ve risk seviyesi olur. Aşağıdaki sayılar hedef olup sprint kabulünün yerine geçmez.

## Sprint 0 — Temel mimari ve GitHub düzeni

- UI/API/worker/veri depolama sınırları, teknoloji seçimleri ve mimari karar kayıtları.
- GitHub Project, sprint milestone'ları, issue/PR şablonları ve CI temeli.
- Test case şeması, sonuç durumları ve müşteri/proje yapılandırma modeli.
- İzin verilen hedefler, sır yönetimi ve veri değiştiren test politikası.

**Kabul:** Temiz ortamda kurulabilen proje iskeleti; geçen temel CI; örnek test tanımı; ilk sprint issue'ları ve mimari karar kaydı.

## Sprint 1 — Çalışan ilk test akışı

- URL ve proje ayarı alan ilk komut/API akışı.
- Tarayıcı worker'ı, iş kuyruğu, timeout, iptal ve kaynak temizleme.
- Kontrolümüzdeki örnek sitede 10 temel smoke testi ve kanıt üretimi.
- Hedef URL doğrulama; dahili adreslere yetkisiz erişimin engellenmesi.

**Kabul:** Bir koşu başlatılır, sonuç saklanır ve tekrar okunur; iptal edilen işin tarayıcısı kapanır; yetkisiz hedef reddedilir.

## Sprint 2 — Keşif ve özellik tespiti

- Sınırlı sayfa keşfi, bağlantı/form/rol/etiket toplama.
- Login, kayıt, arama, ürün ve sepet için ilk kural tabanlı tespit.
- Mevcut, bulunamadı ve belirsiz ayrımı; koşullara göre test planı üretimi.
- Keşif derinliği, istek hızı ve sayfa bütçesi.

**Kabul:** Login olan ve olmayan örnek sitelerde doğru test planı; belirsizlik ve atlama nedenlerinin kaydı; keşif sınırlarına uyum.

## Sprint 3 — UI test havuzu ve element eşleştirme

- Login, form, arama ve gezinme gruplarıyla toplam yaklaşık 40 case.
- Rol, label ve alternatif adlarla element bulma; siteye özel eşleştirme.
- Test verisi hazırlama/temizleme; testler arasında bağımsızlık.
- Yanlış kimlik bilgileri, boş alanlar ve doğrulama mesajları gibi olumsuz senaryolar.

**Kabul:** Farklı buton adları kullanan örneklerde aynı testin çalışması; birden fazla eşleşmede kontrollü belirsizlik; tekrar koşularında açıklanabilir sonuçlar.

## Sprint 4 — API testleri

- Müşterinin sağladığı endpoint veya API sözleşmesi üzerinden yapılandırma.
- Kimlik doğrulama, durum kodu, yanıt şeması ve iş kuralı doğrulamaları.
- UI–API bağlantılı senaryolar; token maskeleme ve işlem sınırları.
- Toplam yaklaşık 60 case.

**Kabul:** Kontrollü örnek API'de başarılı/başarısız doğrulamalar; eksik API ayarında açıklamalı atlama; sırların raporlara sızmaması.

## Sprint 5 — Veritabanı doğrulamaları

- İlk desteklenen veritabanı türü için bağlantı adaptörü.
- Parametreli sorgular, timeout, sınırlı sonuç ve varsayılan salt okunur yetki.
- UI/API işleminin beklenen kaydı oluşturduğunu doğrulama; proje bazlı sorgu şablonları.
- Toplam yaklaşık 75 case.

**Kabul:** Örnek kayıt üzerinde UI/API/veritabanı doğrulaması; bağlantı hatasının test assertion hatasından ayrılması; izinsiz yazma sorgusunun reddi.

## Sprint 6 — Yapay zekâ entegrasyonu

- Sağlayıcıdan bağımsız adaptör ve doğrulanan yapılandırılmış yanıtlar.
- Özellik/sayfa sınıflandırması, test seçimi önerisi ve element bulma desteği.
- Güven eşiği, maliyet/çağrı bütçesi, önbellek ve AI olmadan devam yolu.
- Sayfa içeriğindeki talimatların veri olarak işlenmesi; sır ve kişisel veri azaltımı.
- Kontrolümüzdeki çeşitli örnek sitelerden ölçüm seti.

**Kabul:** Özellik tespiti ve element seçim doğruluğu ölçülür; yanlış kararlar raporlanır; geçersiz/erişilemeyen model yanıtı kontrollü yönetilir; AI test başarı koşulunu değiştiremez.

## Sprint 7 — Web paneli ve proje yönetimi

- Oturum açma, proje oluşturma ve hedef/hesap/API/veritabanı ayarları.
- Test planı inceleme, koşu başlatma/iptal, canlı durum ve koşu geçmişi.
- İlk günden kullanıcı/proje sahipliği kontrolleri; sırların maskeli gösterimi.

**Kabul:** Bir kullanıcı panelden uçtan uca koşu tamamlar; başka kullanıcının proje, sır veya raporlarına erişemez. Bütünleşik MVP gösterimi yapılır.

## Sprint 8 — Raporlama ve kapsam genişletme

- Filtrelenebilir sonuçlar, ekran görüntüleri, hata kanıtları ve dışa aktarım.
- Tekrar koşma, geçmiş karşılaştırma ve kararsız testlerin izlenmesi.
- Öncelikle toplam 100 anlamlı case; 200 case hedefi pilot bulgularına göre sonraki backlog'a bölünür.
- Kanıt saklama süresi ve erişim kontrolleri.

**Kabul:** En az 100 tanımlı case'in uygun örnek ortamlarda doğrulanması; raporların gerçek assertion ve kanıtlarla tutarlı olması; toplam sayı ile koşulabilir sayıların ayrı gösterilmesi.

## Sprint 9 — Domain ve dağıtım

- Staging/production ayrımı, container paketleme ve kontrollü CI/CD.
- Domain/DNS, HTTPS, ortam sırları, migration ve geri dönüş akışı.
- Worker izolasyonu; ağ/CPU/bellek/eşzamanlılık limitleri.
- İzleme, loglar, yedekleme/geri yükleme ve operasyon kılavuzu.

**Kabul:** Staging üzerinde uçtan uca koşu; geri dönüş ve yedekten dönüş denemesi; domain üzerinde HTTPS erişimi; üretim yayını için somut sürüm ve dağıtım planı. Domain satın alma ve ücretli hizmet seçimi kullanıcıya aittir.

## Sprint 10 — Müşterili kullanım ve pilot

- Organizasyonlar, roller, kotalar ve müşteri bazında kaynak/maliyet takibi.
- Eşzamanlı koşular ve müşteri verisi izolasyonunun güçlendirilmesi.
- Özel ağlar için müşteride çalışan agent pilotu ve dışarı yönlü güvenli bağlantı modeli.
- Pilot geri bildirimleri, kullanım rehberi ve destek süreçleri.

**Kabul:** En az iki örnek müşteri ortamında izolasyon ve kota doğrulaması; özel ağ agent gösterimi; pilot sorunlarının önceliklendirilmiş backlog'u.

Ödeme/abonelik sistemi, kapsamlı yük testi ve otomatik güvenlik taraması ayrı ürün kararlarıdır; bu planın temel 100–200 fonksiyonel test hedefiyle aynı kapsamda sayılmaz.
