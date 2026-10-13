"""Sofascore 403'unun sebebini olcer (gecici teshis araci).

Cevaplamasi gereken iki soru:
  1. curl_cffi gercekten kurulu mu? (kurulu degilse sofa_session duz requests'e
     duser ve Python TLS parmak izi yuzunden 403 alir)
  2. Kuruluysa impersonation yetiyor mu, yoksa IP'nin kendisi mi engelli?
"""
import sys

API = "https://www.sofascore.com/api/v1/sport/football/events/live"
SITE = "https://www.sofascore.com/"
BASLIK = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Origin": "https://www.sofascore.com",
    "Referer": "https://www.sofascore.com/",
}


def rapor(ad, yanit):
    govde = ""
    try:
        govde = yanit.text[:300].replace("\n", " ")
    except Exception as e:
        govde = f"(govde okunamadi: {e})"
    print(f"\n--- {ad}")
    print(f"    durum        : {yanit.status_code}")
    print(f"    'challenge'  : {'challenge' in govde}")
    print(f"    govde (300)  : {govde}")


print("=" * 70)
print("  SOFASCORE TESHIS")
print("=" * 70)

try:
    from curl_cffi import requests as curl_requests
    print(f"\n[1] curl_cffi KURULU (surum: {getattr(__import__('curl_cffi'), '__version__', '?')})")
    var = True
except ImportError as e:
    print(f"\n[1] curl_cffi YOK -> {e}")
    var = False

import requests as std

# Duz requests (sofa_session'in curl_cffi yokken kullandigi yol)
s = std.Session(); s.headers.update(BASLIK)
try:
    rapor("duz requests / ana sayfa", s.get(SITE, timeout=20))
    rapor("duz requests / API", s.get(API, timeout=20))
except Exception as e:
    print(f"\n--- duz requests HATA: {e}")

# curl_cffi impersonate (sofa_session'in asil yolu)
if var:
    for kimlik in ("safari", "chrome"):
        try:
            c = curl_requests.Session(impersonate=kimlik)
            c.headers.update(BASLIK)
            rapor(f"curl_cffi impersonate={kimlik} / API", c.get(API, timeout=20))
        except Exception as e:
            print(f"\n--- curl_cffi {kimlik} HATA: {e}")

print("\n" + "=" * 70)
print("  YORUM")
print("  - Hepsi 403 ve 'challenge' False  -> IP engeli, impersonation cozmez")
print("  - impersonate 200 donuyorsa       -> sorun yalnizca curl_cffi eksikligiydi")
print("  - 403 ama 'challenge' True        -> tarayici fallback'i devreye girmeli")
print("=" * 70)
