# GitHub sprint iş akışı

## Kurulum

GitHub deposu: https://github.com/mehtapkirkgoz/Adaptive-QA-Project (özel depo). Bu dosya yapılacak düzeni tanımlar; GitHub Project, milestone veya issue oluşturulduğu anlamına gelmez.

- Project sütunları: Backlog, Ready, In Progress, In Review, Done.
- Her sprint için milestone: `Sprint 0 — Temel mimari` gibi.
- Her iş için issue: amaç, kapsam, kabul koşulları ve doğrulama yöntemi.
- Etiketler: `type:feature`, `type:bug`, `type:docs`, `type:infra`, `area:ui`, `area:api`, `area:db`, `area:ai`.

## Sprint başlangıcı

1. Kapasiteye uygun issue'ları sprint milestone'ına al.
2. Sprint takip issue'su aç: `Sprint N başladı — <hedef>`.
3. Başlangıç/hedef tarihini, hedefi ve bağlı issue'ları yaz.
4. README durumunu `Devam ediyor` yap ve takip issue'suna bağla.

Bir plan dosyasının eklenmesi tek başına sprintin başladığı anlamına gelmez.

## Geliştirme

1. Issue için `codex/<issue-no>-<kisa-aciklama>` dalı aç.
2. Küçük ve incelenebilir PR oluştur; issue'yu `Closes #...` ile ilişkilendir.
3. PR'a davranış değişikliği, doğrulama ve kalan sınırlamaları yaz.
4. Gerekli CI ve inceleme tamamlanınca birleştir; issue'yu Done yap.

## Sprint bitişi

1. Kabul koşullarını ve demo senaryosunu doğrula.
2. Eksik işleri açıkça sonraki backlog'a taşı; tamamlandı diye işaretleme.
3. README'ye teslim edilen işleri, PR'ları ve varsa sürüm bağlantısını ekle.
4. Takip issue'suna `Sprint N bitti` özeti ekle: teslimatlar, doğrulama, kalan işler ve kısa değerlendirme.
5. Sprint hedefi karşılandıysa milestone ve takip issue'sunu kapat. Çalışma dönemi bittiği halde hedef eksikse README'de `Kısmen tamamlandı` yaz.
6. Dağıtılabilir artış varsa sürüm notu ve uygun sürüm etiketi oluştur. Her sprint zorunlu olarak üretime çıkmaz.

## Tamamlanma ölçütü

- Issue kabul koşulları karşılandı ve ilgili kontroller geçti.
- Gereken hata/olumsuz senaryolar doğrulandı.
- Sır veya müşteri verisi kaynak koda/loga eklenmedi.
- Kullanımı etkileyen değişiklikler belgelendi.
- PR birleştirildi; README ve sprint kaydı gerçeği yansıtıyor.
