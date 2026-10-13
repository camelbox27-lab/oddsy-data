"""Sofascore erisim teshisi.

SOFA_PROXY secret'i tanimliysa istekler oradan gecer (HTTPS_PROXY env).
Amac: proxy'nin gercekten devrede olup olmadigini ve Sofascore'un 200 donup
donmedigini olcmek.

NOT: Proxy adresi secret'tan okunur, asla ekrana basilmaz; yalnizca cikis IP'si
gosterilir.
"""
import os

API = "https://www.sofascore.com/api/v1/sport/football/events/live"
IP_SERVIS = "https://api.ipify.org?format=json"
BASLIK = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Origin": "https://www.sofascore.com",
    "Referer": "https://www.sofascore.com/",
}

print("=" * 70)
print("  SOFASCORE TESHIS")
print("=" * 70)

proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
if proxy:
    # Kimlik bilgisi sizdirmadan yalnizca sema + host goster
    gorunur = proxy.split("@")[-1] if "@" in proxy else proxy
    print(f"\n[0] Proxy TANIMLI  -> ...@{gorunur}" if "@" in proxy else f"\n[0] Proxy TANIMLI  -> {gorunur}")
else:
    print("\n[0] Proxy YOK (dogrudan GitHub IP'si kullanilacak)")

try:
    from curl_cffi import requests as curl_requests
    print("[1] curl_cffi kurulu")
except ImportError:
    curl_requests = None
    print("[1] curl_cffi YOK")

import requests as std


def dene(ad, oturum):
    # Cikis IP'si: proxy gercekten devrede mi?
    try:
        ip = oturum.get(IP_SERVIS, timeout=25).json().get("ip", "?")
    except Exception as e:
        ip = f"(alinamadi: {e})"
    print(f"\n--- {ad}")
    print(f"    cikis IP : {ip}")
    try:
        y = oturum.get(API, timeout=25)
        govde = y.text[:200].replace("\n", " ")
        print(f"    Sofascore: {y.status_code}  {'BASARILI' if y.status_code == 200 else ''}")
        print(f"    govde    : {govde}")
    except Exception as e:
        print(f"    Sofascore HATA: {e}")


s = std.Session(); s.headers.update(BASLIK)
dene("duz requests", s)

if curl_requests:
    c = curl_requests.Session(impersonate="safari"); c.headers.update(BASLIK)
    dene("curl_cffi impersonate=safari", c)

print("\n" + "=" * 70)
print("  YORUM")
print("  Sofascore 200  -> proxy ise yariyor, MENU calisabilir")
print("  Sofascore 403  -> bu IP de engelli (datacenter proxy ise beklenen)")
print("  cikis IP degismediyse -> proxy hic devreye girmemis")
print("=" * 70)
