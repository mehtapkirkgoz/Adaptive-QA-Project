# Geliştirici kurulumu — Aşama 0.1

Gerekenler: Git ve Python 3.13 veya üzeri. Bu bilgisayarda Python 3.13, Python 3.14, Node.js ve Git tespit edildi. Bu aşamada Node.js, Docker, veritabanı, tarayıcı paketi veya AI anahtarı gerekmez.

Repo klasöründe PowerShell komutları:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m adaptive_qa --status
```

Sanal ortamı aktive etmek zorunlu değildir. Bu nedenle PowerShell execution policy değiştirmek gerekmez.

Kontrol:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src
```

Beklenen durum mesajı Sprint 0 iskeletinin hazır olduğunu ve test motorunun henüz uygulanmadığını belirtir. Bu komut siteyi test etmez.

Paketin çalışma zamanı bağımlılığı yoktur. Kurulum paketleme aracı setuptools'u yükleyebilir. Bağımlılık kilidi ilk harici çalışma zamanı paketi eklendiğinde hazırlanacak.

Sonraki aşama: test case/veri sözleşmeleri ve proje politikası. Playwright ve Chromium kurulumu Sprint 1'de, API/veritabanı servisleri ilgili aşamada belgelenecek.
