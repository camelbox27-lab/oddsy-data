"""Mackolik 403'unun sebebini olcer.

Durum: mac LISTESI (JSON API) calisiyor, ama her macin /iddaa/ HTML sayfasi
403 donuyor. Yani duz IP yasagi degil. Bu script hangi yontemin 200
aldigini olcer, boylece dogru duzeltme tahminle degil olcumle secilir.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "kaynak"))
import tkinter_stub                      # noqa: E402
tkinter_stub.kur()
import datetime as dt                    # noqa: E402
import iddaapro as ip                    # noqa: E402

BASLIK = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) '
                   'Gecko/20100101 Firefox/120.0'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'tr,en-US;q=0.7,en;q=0.3',
}

print("=" * 70)
print("  MACKOLIK TESHIS")
print("=" * 70)

# --- Once liste API'si: gercek bir mac linki lazim
gun = dt.date.today()
ozetler = ip.fetch_matches_api(gun, lig_filtre=ip._get_all_league_keys(),
                               uefa_kupalari=True)
print(f"\n[1] Liste API ({gun:%d.%m.%Y}): {len(ozetler)} mac")
if not ozetler:
    print("    Liste de bos -> sorun yalnizca HTML sayfalarinda degil.")
    sys.exit(1)

url = ozetler[0]['iddaa_link']
print(f"[2] Test edilecek mac sayfasi:\n    {url}")


def dene(ad, getir):
    try:
        y = getir()
    except Exception as e:
        print(f"\n--- {ad}\n    HATA: {e}")
        return
    govde = ""
    try:
        govde = y.text[:120].replace("\n", " ")
    except Exception:
        pass
    iyi = y.status_code == 200
    # Oran tablosu gercekten geldi mi?
    piyasa = ip.MARKET_ITEM_CLASS in (y.text or "") if iyi else False
    print(f"\n--- {ad}")
    print(f"    durum     : {y.status_code}  {'<-- BASARILI' if iyi else ''}")
    print(f"    oran var  : {piyasa}")
    print(f"    govde     : {govde}")


import requests as std                   # noqa: E402

# a) Mevcut yontem: duz requests
s = std.Session(); s.headers.update(BASLIK)
dene("duz requests (su anki yontem)", lambda: s.get(url, timeout=20))

# b) Duz requests + once ana sayfa (cerez isinmasi)
s2 = std.Session(); s2.headers.update(BASLIK)
try:
    s2.get("https://www.mackolik.com/", timeout=20)
except Exception:
    pass
dene("duz requests + ana sayfa isinmasi", lambda: s2.get(url, timeout=20))

# c) curl_cffi: tarayici TLS parmak izi
try:
    from curl_cffi import requests as curl_requests
    for kimlik in ("chrome", "safari", "firefox"):
        try:
            c = curl_requests.Session(impersonate=kimlik)
            c.headers.update(BASLIK)
            dene(f"curl_cffi impersonate={kimlik}", lambda c=c: c.get(url, timeout=20))
        except Exception as e:
            print(f"\n--- curl_cffi {kimlik}\n    KURULAMADI: {e}")
except ImportError:
    print("\n--- curl_cffi YOK (kurulu degil)")

print("\n" + "=" * 70)
print("  YORUM")
print("  curl_cffi 200 + oran var -> TLS parmak izi sorunu, cozum impersonation")
print("  isinma 200 verirse       -> cerez sorunu, ana sayfa ziyareti yeter")
print("  hepsi 403                -> IP engeli, proxy gerekir")
print("=" * 70)
