"""livedata dizisindeki alan konumlarini KIYASLAYARAK bulur.

HTML'den cekilmis gercek oranlari bilinen maclarla karsilastirir, boylece
hangi indeks hangi markete denk geliyor tahminle degil eslestirerek cikar.
"""
import datetime as dt
import json
import sys

import requests as std

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

# HTML'den cekilmis dogrulanmis oranlar (kiyas icin)
KIYAS = {
    "3224058": {"mac": "PSG - Barcelona", "MS1": "2.14", "MS0": "3.85", "MS2": "2.17",
                "AU2.5Alt": "4.28", "CS1X": "1.28", "CS12": "1.23", "CSX2": "1.28",
                "KGVar": "2.33", "KGYok": "1.60", "IY1": "2.66", "IY0": "2.87", "IY2": "2.67"},
}

gun = dt.date.today()
url = f"https://vd.mackolik.com/livedata?date={gun:%d/%m/%Y}"
s = std.Session(); s.headers.update({'User-Agent': UA, 'Accept': '*/*'})
veri = s.get(url, timeout=30).json()
maclar = veri.get('m', [])

print("=" * 70)
print(f"  ALAN KONUMU ESLESTIRME  ({len(maclar)} mac)")
print("=" * 70)

for kod, dogru in KIYAS.items():
    bulundu = None
    for m in maclar:
        if any(str(x) == kod for x in m if not isinstance(x, (list, dict))):
            bulundu = m
            break
    print(f"\n### {dogru['mac']}  (iddaa kodu {kod})")
    if not bulundu:
        print("    livedata'da BULUNAMADI")
        continue

    print("    --- dizi (indeks: deger) ---")
    for i, v in enumerate(bulundu):
        if isinstance(v, (list, dict)):
            v = f"<{type(v).__name__}>"
        print(f"      [{i:2}] {v!r}")

    print("    --- eslesme ---")
    for ad, beklenen in dogru.items():
        if ad == "mac":
            continue
        yerler = [i for i, v in enumerate(bulundu)
                  if not isinstance(v, (list, dict)) and str(v) == beklenen]
        print(f"      {ad:10} = {beklenen:6} -> indeks {yerler if yerler else 'YOK'}")

# Ikinci bir mac: konumlar tutarli mi?
print("\n### Tutarlilik kontrolu (ilk 3 mac, indeks 16-26 araligi)")
for m in maclar[:3]:
    ad = f"{m[2]} - {m[4]}" if len(m) > 4 else "?"
    dilim = [m[i] if i < len(m) and not isinstance(m[i], (list, dict)) else None
             for i in range(16, 27)]
    print(f"  {ad[:34]:34} {dilim}")
print("=" * 70)
