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


Sonraki aşama: test case/veri sözleşmeleri ve proje politikası. Playwright ve Chromium kurulumu Sprint 1'de, API/veritabanı servisleri ilgili aşamada belgelenecek.


## Browser Automation Dependencies

Install the pinned runtime dependencies and project package:

```powershell
python -m pip install -r requirements.lock.txt
python -m pip install --no-deps -e .
```

Install the Chromium browser used by Playwright:

```powershell
python -m playwright install chromium
```

The browser binary is installed separately and must not be committed.

The runtime dependency snapshot was initially verified on Windows
with Python 3.13. Other supported environments require CI verification.