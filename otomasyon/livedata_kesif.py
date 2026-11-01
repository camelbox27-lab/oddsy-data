"""vd.mackolik.com/livedata dizisinde hangi alanin hangi market oldugunu bulur.

NEDEN: Iddaa'nin alt/ust oranlari Mackolik'in mac sayfalarindan geliyor, o
sayfalar GitHub IP'sinden 403. livedata akisi engellenmemis ve icinde MS
oranlarinin yani sira baska oranlar da var ama konumlari belgesiz.

YONTEM: iddaa/gunluk/gunlukmaclar.json icinde oranlari DOLU olan maclar
dogrulama kaynagi olarak kullanilir. Her mac icin dizide beklenen degerin
bulundugu konumlar toplanir, sonra tum maclarda KESISTIRILIR. Tek bir konum
kalirsa o marketin yeri kesinlesmis olur; birden fazla veya sifir kalirsa
guvenilir degildir ve kullanilmaz.

Bu script veri yazmaz, sadece rapor basar.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests

KOK = Path(__file__).resolve().parent.parent
IDDAA = KOK / "iddaa" / "gunluk" / "gunlukmaclar.json"
KAYNAK = "https://vd.mackolik.com/livedata"
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

# Iddaa dosyasindaki alan -> rapordaki ad
MARKETLER = {
    'MS1': 'MS1', 'MS0': 'MS0', 'MS2': 'MS2',
    'AU 2.5 Ust': '2.5 UST', 'AU 2.5 Alt': '2.5 ALT',
    'AU 1.5 Ust': '1.5 UST', 'AU 1.5 Alt': '1.5 ALT',
    'AU 3.5 Ust': '3.5 UST', 'AU 3.5 Alt': '3.5 ALT',
    'KG Var': 'KG VAR', 'KG Yok': 'KG YOK',
    'IY1': 'IY1', 'IY0': 'IY0', 'IY2': 'IY2',
}


def _sayi(v):
    s = str(v or '').strip().replace(',', '.')
    if not s:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    return round(f, 2) if f > 1 else None


def main():
    gun = dt.date.today()
    if len(sys.argv) > 1:
        gun = dt.datetime.strptime(sys.argv[1], "%d.%m.%Y").date()

    if not IDDAA.exists():
        print(f"HATA: {IDDAA} yok."); return 1
    iddaa = json.loads(IDDAA.read_text(encoding='utf-8'))

    # Dogrulama icin: 2.5 Ust'u dolu olan maclar (en az bilgi veren alan bu)
    dogrulama = {str(r.get('MS Kodu') or '').strip(): r
                 for r in iddaa if r.get('AU 2.5 Ust')}
    print(f"Iddaa dosyasinda {len(iddaa)} mac, oranlari dolu olan {len(dogrulama)}")
    if not dogrulama:
        print("Dogrulama yapilacak mac yok; iddaa butonuna basip tekrar dene.")
        return 1

    try:
        y = requests.get(f"{KAYNAK}?date={gun:%d/%m/%Y}",
                         headers={'User-Agent': UA, 'Accept': '*/*'}, timeout=30)
        y.raise_for_status()
        maclar = y.json().get('m', [])
    except Exception as e:
        print(f"HATA: livedata alinamadi: {e}")
        return 1
    print(f"livedata: {len(maclar)} mac, dizi uzunlugu "
          f"{sorted({len(m) for m in maclar if isinstance(m, list)})}")

    # kod -> dizi
    KOD = 14
    akis = {}
    for m in maclar:
        if isinstance(m, list) and len(m) > KOD:
            k = str(m[KOD] or '').strip()
            if k and k != '0':
                akis[k] = m

    ortak = sorted(set(akis) & set(dogrulama))
    print(f"Iki tarafta da bulunan mac: {len(ortak)}\n")
    if not ortak:
        print("Eslesen mac yok; iddaa bulteni baska bir gune ait olabilir.")
        return 1

    # Her market icin konum kesisimi
    for alan, ad in MARKETLER.items():
        kesisim = None
        kullanilan = 0
        for kod in ortak:
            beklenen = _sayi(dogrulama[kod].get(alan))
            if beklenen is None:
                continue
            dizi = akis[kod]
            konumlar = {i for i, v in enumerate(dizi) if _sayi(v) == beklenen}
            kesisim = konumlar if kesisim is None else (kesisim & konumlar)
            kullanilan += 1
        if not kullanilan:
            print(f"  {ad:8s}: dogrulama verisi yok")
        elif kesisim:
            isaret = "KESIN" if len(kesisim) == 1 else "belirsiz"
            print(f"  {ad:8s}: konum {sorted(kesisim)}  ({kullanilan} macla, {isaret})")
        else:
            print(f"  {ad:8s}: tutarli konum YOK ({kullanilan} mac denendi)")

    # Elle bakmak icin bir ornek
    kod = ortak[0]
    r = dogrulama[kod]
    print(f"\nOrnek mac {kod}: {r['Ev Sahibi']} - {r['Konuk Ekip']}")
    print("  iddaa:", {a: r.get(a) for a in MARKETLER if r.get(a)})
    print("  dizi:")
    for i, v in enumerate(akis[kod]):
        if _sayi(v) is not None:
            print(f"    [{i:3d}] {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
