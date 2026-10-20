"""vd.mackolik.com/livedata akisinin yapisini dokar.

Bulgu: /mac/.../iddaa/ HTML ve perform/p0/ajax uclari GitHub IP'sinden 403,
ama vd.mackolik.com/livedata 200 donuyor ve icinde 'odd' geciyor.

Soru: bu akis IddaaPro'nun ihtiyaci olan marketleri (MS, CS, IY, AU, KG,
HND, IY/MS, TG, takim gol) iceriyor mu, yoksa sadece MS mi?
"""
import json
import re
import sys
import datetime as dt

import requests as std

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

gun = dt.date.today()
url = f"https://vd.mackolik.com/livedata?date={gun:%d/%m/%Y}"
print("=" * 70)
print("  vd.mackolik.com/livedata YAPISI")
print("=" * 70)
print(f"\nURL: {url}")

s = std.Session(); s.headers.update({'User-Agent': UA, 'Accept': '*/*'})
y = s.get(url, timeout=30)
g = y.text
print(f"durum: {y.status_code} | tip: {y.headers.get('Content-Type')} | uzunluk: {len(g)}")

print("\n--- ilk 600 karakter ---")
print(g[:600])

# JSON mu?
veri = None
try:
    veri = y.json()
    print("\n[OK] Dogrudan JSON")
except Exception:
    m = re.search(r'\{.*\}|\[.*\]', g, re.S)
    if m:
        try:
            veri = json.loads(m.group(0))
            print("\n[OK] Govde icinden JSON ayiklandi")
        except Exception as e:
            print(f"\n[!] JSON ayiklanamadi: {e}")

if veri is None:
    print("\n--- son 400 karakter ---")
    print(g[-400:])
    sys.exit("JSON degil; bicimi elle incelemek gerek.")

print(f"\n--- ust seviye tip: {type(veri).__name__}")
if isinstance(veri, dict):
    print(f"    anahtarlar: {list(veri.keys())[:25]}")
    # en uzun listeyi mac listesi say
    aday = max(((k, v) for k, v in veri.items() if isinstance(v, list)),
               key=lambda kv: len(kv[1]), default=(None, []))
    ad, maclar = aday
    print(f"    mac listesi gibi duran anahtar: {ad} ({len(maclar)} oge)")
elif isinstance(veri, list):
    maclar = veri
    print(f"    {len(maclar)} oge")
else:
    sys.exit("Beklenmeyen yapi.")

if not maclar:
    sys.exit("Mac listesi bos.")

ornek = maclar[0]
print(f"\n--- ilk mac ogesinin tipi: {type(ornek).__name__}")
print(json.dumps(ornek, ensure_ascii=False, indent=1)[:2500])

# Oran gibi duran alanlari ara
print("\n--- 'odd' gecen alanlar (tum akista) ---")
bulunan = sorted(set(re.findall(r'"([^"]*odd[^"]*)"', g, re.I)))[:40]
print("   ", bulunan or "yok")

print("\n--- iddaa kodu gecen alanlar ---")
print("   ", sorted(set(re.findall(r'"([^"]*(?:iddaa|code|kod)[^"]*)"', g, re.I)))[:30])
print("=" * 70)
